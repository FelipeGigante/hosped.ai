import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from .agent import build_agent
from .guardrails import GuardrailError, validate_input, validate_output
from .session import load_history, save_history
from .whatsapp import parse_inbound, send_message, send_typing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_agent_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_executor
    # Warm up vector store (downloads model on first run)
    from .vector_store import get_store
    get_store()
    _agent_executor = build_agent()
    logger.info("Agent ready")
    yield


app = FastAPI(title="hosped.ai", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives Evolution API webhook and dispatches processing in background."""
    payload = await request.json()
    parsed = parse_inbound(payload)

    if not parsed:
        return JSONResponse({"status": "ignored"})

    user_id, text = parsed
    background_tasks.add_task(_process, user_id, text)
    return JSONResponse({"status": "accepted"})


async def _process(user_id: str, text: str) -> None:
    """Full pipeline: guardrail → agent → guardrail → respond."""
    try:
        # --- Input guardrail ---
        try:
            clean_text = validate_input(text)
        except GuardrailError as e:
            await send_message(user_id, e.user_message)
            return

        history = load_history(user_id)

        await send_typing(user_id, duration_ms=2000)

        # --- Agent ---
        result = _agent_executor.invoke({
            "input": clean_text,
            "chat_history": history,
        })
        response = result.get("output", "Desculpe, tive um problema interno. Pode repetir? 🙏")

        # --- Output guardrail ---
        response = validate_output(response)

        # --- Persist history (keep last 20 messages = 10 turns) ---
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
