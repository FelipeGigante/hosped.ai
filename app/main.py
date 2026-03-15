import json
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from .agent import build_agent
from .guardrails import GuardrailError, validate_input, validate_output
from .session import load_history, save_history, load_state, save_state
from .whatsapp import parse_inbound, send_message, send_typing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_agent_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_executor
    from .vector_store import get_store
    get_store()
    _agent_executor = build_agent()
    logger.info("Agent ready")
    yield


app = FastAPI(title="hosped.ai", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def webhook(request: Request, background_tasks: BackgroundTasks, event_path: str = ""):
    payload = await request.json()
    logger.info("Webhook received: event=%s path=%s", payload.get("event"), event_path)
    parsed = parse_inbound(payload)
    if not parsed:
        return JSONResponse({"status": "ignored"})
    user_id, text = parsed
    background_tasks.add_task(_process, user_id, text)
    return JSONResponse({"status": "accepted"})

app.add_api_route("/webhook", webhook, methods=["POST"])
app.add_api_route("/webhook/{event_path:path}", webhook, methods=["POST"])


def _format_state_context(state: dict) -> str:
    """Format trip state as context block injected into agent input."""
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
            dest = state.get("destination", "desconhecido")
            key = f"no_hotels_{dest.lower().replace(' ', '_')}"
            if key not in state["errors_shown"]:
                state["errors_shown"].append(key)

        elif tool_name == "confirm_booking" and isinstance(result, dict):
            if result.get("hotel_name"):
                state["confirmed_hotel_id"] = result.get("hotel_id", "")
                state["confirmed_hotel_name"] = result["hotel_name"]
                state["phase"] = "confirmed"

    return state


async def _process(user_id: str, text: str) -> None:
    """Full pipeline: guardrail → agent → guardrail → respond."""
    try:
        try:
            clean_text = validate_input(text)
        except GuardrailError as e:
            await send_message(user_id, e.user_message)
            return

        history = load_history(user_id)
        state = load_state(user_id)

        await send_typing(user_id, duration_ms=2000)

        state_context = _format_state_context(state)
        agent_input = clean_text + state_context if state_context else clean_text

        result = _agent_executor.invoke({
            "input": agent_input,
            "chat_history": history,
        })

        response = result.get("output", "Desculpe, tive um problema interno. Pode repetir? 🙏")
        response = validate_output(response)

        updated_state = _update_state(state, result.get("intermediate_steps", []))
        save_state(user_id, updated_state)

        history.append(HumanMessage(content=clean_text))
        history.append(AIMessage(content=response))
        save_history(user_id, history[-20:])

        await send_message(user_id, response)

    except Exception:
        logger.exception("Unhandled error for user %s", user_id)
        try:
            await send_message(user_id, "Tive um problema técnico. Pode tentar novamente? 🙏")
        except Exception:
            pass
