import asyncio
import json
import logging
import random
import re
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from .agent import build_agent
from .guardrails import GuardrailError, validate_input, validate_output
from .memory.profile_store import format_profile_context, load_profile, upsert_profile
from .queue import enqueue
from .session import load_history, save_history, load_state, save_state
from .whatsapp import parse_inbound, send_message, send_typing
from .worker import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_agent_executor = None

# ---------------------------------------------------------------------------
# Greeting fast path — respond in <2 s without touching the LLM
# ---------------------------------------------------------------------------
_EXACT_GREETINGS = frozenset([
    "oi", "olá", "ola", "hey", "hi", "hello", "e aí", "eai", "opa",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom",
    "tudo", "oi tudo bem", "oi tudo bom",
])
_GREETING_RE = re.compile(
    r"^(oi|ol[aá]|hey|hi|hello|e\s?a[ií]|opa|bom\s?dia|boa\s?tarde|boa\s?noite"
    r"|tudo\s?(bem|bom)?)[!?.,\s]*$",
    re.IGNORECASE | re.UNICODE,
)
_GREETING_RESPONSES = [
    "Oi! 🦜 Sou o Zeca, da Zarpa. Pra onde você tá pensando em ir?",
    "Olá! Sou o Zeca, maritaca da Zarpa 🦜 Qual é o destino da sua próxima viagem?",
    "Boa! Sou o Zeca 🦜 Pronto pra encontrar a hospedagem perfeita pra você. Qual cidade?",
    "Ei, chegou na hora certa! 🦜 Sou o Zeca da Zarpa. Me conta: pra onde vai?",
]


def _is_greeting(text: str) -> bool:
    t = text.strip().lower()
    return t in _EXACT_GREETINGS or bool(_GREETING_RE.match(t))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_executor
    _agent_executor = build_agent()
    logger.info("Agent ready")
    worker_task = asyncio.create_task(run_worker(_process))
    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="hosped.ai", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


async def webhook(request: Request, background_tasks: BackgroundTasks, event_path: str = ""):
    payload = await request.json()
    logger.info("Webhook received: event=%s path=%s", payload.get("event"), event_path)
    parsed = parse_inbound(payload)
    if not parsed:
        return JSONResponse({"status": "ignored"})
    user_id, text = parsed

    # Fast path: greetings bypass the LLM entirely
    if _is_greeting(text):
        logger.info("Greeting fast path for %s", user_id)
        background_tasks.add_task(send_message, user_id, random.choice(_GREETING_RESPONSES))
        return JSONResponse({"status": "accepted", "path": "greeting"})

    # Enqueue to Redis when available (multi-instance safe); fallback to BackgroundTasks
    if enqueue(user_id, text):
        logger.info("Enqueued message for %s", user_id)
    else:
        background_tasks.add_task(_process, user_id, text)

    return JSONResponse({"status": "accepted"})

app.add_api_route("/webhook", webhook, methods=["POST"])
app.add_api_route("/webhook/{event_path:path}", webhook, methods=["POST"])


def _format_state_context(state: dict) -> str:
    """Format current trip state as context block injected into agent input."""
    parts = []
    if state.get("destination"):
        parts.append(f"• Destino: {state['destination']}")
    if state.get("checkin"):
        parts.append(f"• Check-in: {state['checkin']}")
    if state.get("checkout"):
        parts.append(f"• Check-out: {state['checkout']}")
    if state.get("guests"):
        parts.append(f"• Hóspedes: {state['guests']}")
    if state.get("budget_per_night"):
        parts.append(f"• Orçamento: R$ {state['budget_per_night']:.0f}/noite")
    if state.get("preferences"):
        parts.append(f"• Preferências: {', '.join(state['preferences'])}")
    if state.get("trip_type"):
        parts.append(f"• Tipo de viagem: {state['trip_type']}")
    if state.get("confirmed_hotel_name"):
        parts.append(f"• Hotel confirmado: {state['confirmed_hotel_name']}")
    if state.get("errors_shown"):
        parts.append(f"• Erros já exibidos ao usuário: {', '.join(state['errors_shown'])}")
    if state.get("phase") and state["phase"] != "collecting":
        parts.append(f"• Fase: {state['phase']}")
    if not parts:
        return ""
    return "\n\n[CONTEXTO SALVO DA CONVERSA]\n" + "\n".join(parts) + "\n[FIM DO CONTEXTO]"


def _update_state(state: dict, intermediate_steps: list) -> dict:
    """Extract state updates from agent tool calls."""
    for action, output in intermediate_steps:
        tool_name = getattr(action, "tool", "")
        try:
            result = json.loads(output) if isinstance(output, str) else output
        except (json.JSONDecodeError, TypeError):
            continue

        if tool_name == "extract_trip_intent" and isinstance(result, dict):
            for src, dst in [
                ("destination", "destination"),
                ("checkin_date", "checkin"),
                ("checkout_date", "checkout"),
                ("guests", "guests"),
                ("budget_per_night", "budget_per_night"),
                ("trip_type", "trip_type"),
            ]:
                if result.get(src):
                    state[dst] = result[src]
            if result.get("preferences"):
                state["preferences"] = result["preferences"]

        elif tool_name == "search_hotels" and isinstance(result, dict) and "error" in result:
            dest = state.get("destination") or "desconhecido"
            key = f"no_hotels_{dest.lower().replace(' ', '_')}"
            if key not in state["errors_shown"]:
                state["errors_shown"].append(key)

        elif tool_name == "search_hotels" and isinstance(result, dict) and "fonte" in result:
            state["inventory_source"] = result["fonte"]

        elif tool_name == "create_booking_handoff" and isinstance(result, dict):
            if result.get("hotel_name"):
                state["confirmed_hotel_id"] = result.get("hotel_id", "")
                state["confirmed_hotel_name"] = result["hotel_name"]
                state["phase"] = "confirmed"

        elif tool_name == "book_hotel" and isinstance(result, dict):
            if result.get("booking_confirmed"):
                state["confirmed_hotel_name"] = state.get("confirmed_hotel_name", "")
                state["booking_reference"] = result.get("booking_id", "")
                state["phase"] = "confirmed"

    return state


async def _process(user_id: str, text: str) -> None:
    """Full pipeline: guardrail → load profile + session → agent → guardrail → respond."""
    try:
        # 1. Input guardrail (no LLM, cheap)
        try:
            clean_text = validate_input(text)
        except GuardrailError as e:
            await send_message(user_id, e.user_message)
            return

        # 2. Load session (Redis / in-memory)
        history = load_history(user_id)
        state = load_state(user_id)

        # 3. Load persistent profile (PostgreSQL — personalization layer)
        profile = await load_profile(user_id)
        profile_context = format_profile_context(profile)

        # 4. Show typing indicator
        await send_typing(user_id, duration_ms=2000)

        # 5. Build agent input = message + profile context + trip state context
        state_context = _format_state_context(state)
        agent_input = clean_text
        if profile_context:
            agent_input += f"\n\n{profile_context}"
        if state_context:
            agent_input += state_context

        # 6. Run agent
        result = _agent_executor.invoke({
            "input": agent_input,
            "chat_history": history,
        })

        response = result.get("output", "Desculpe, tive um problema interno. Pode repetir? 🙏")

        # 7. Output guardrail
        response = validate_output(response)

        # 8. Update session state
        updated_state = _update_state(state, result.get("intermediate_steps", []))
        save_state(user_id, updated_state)

        # 9. Update history (keep last 20 messages)
        history.append(HumanMessage(content=clean_text))
        history.append(AIMessage(content=response))
        save_history(user_id, history[-20:])

        # 10. Send response ASAP — before any non-critical I/O
        await send_message(user_id, response)

        # 11. Update profile: last seen + preferences from this interaction (non-blocking path)
        await upsert_profile(user_id, {
            "phone": user_id.split("@")[0],
            "preferred_trip_types": [updated_state["trip_type"]] if updated_state.get("trip_type") else [],
            "preferred_amenities": updated_state.get("preferences", []),
        })

    except Exception:
        logger.exception("Unhandled error for user %s", user_id)
        try:
            await send_message(user_id, "Tive um problema técnico. Pode tentar novamente? 🙏")
        except Exception:
            pass
