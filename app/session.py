"""Session store with Redis backend and in-memory fallback.

Redis is used when REDIS_URL is set (production/staging).
Falls back to in-memory dict when Redis is unavailable (local dev without Docker).

Session TTL: 24h (configurable via SESSION_TTL_SECONDS env var).
"""

import json
import logging
import os
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

_TTL = int(os.getenv("SESSION_TTL_SECONDS", "900"))  # 15 min inactivity default

# ─────────────────────────────────────────────────────────────────────────────
# Redis client (lazy init, optional)
# ─────────────────────────────────────────────────────────────────────────────

_redis_client: Any = None
_redis_available = False


def _get_redis():
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        _redis_available = False
        return None

    try:
        import redis
        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Redis session store connected: %s", redis_url)
        return _redis_client
    except Exception as e:
        logger.warning("Redis unavailable (%s) — using in-memory session store", e)
        _redis_available = False
        return None


# ─────────────────────────────────────────────────────────────────────────────
# In-memory fallback
# ─────────────────────────────────────────────────────────────────────────────

_history_store: dict[str, tuple[list[BaseMessage], float]] = {}
_state_store: dict[str, tuple[dict, float]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Message serialization for Redis
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_messages(messages: list[BaseMessage]) -> str:
    return json.dumps([
        {"type": m.__class__.__name__, "content": m.content}
        for m in messages
    ], ensure_ascii=False)


def _deserialize_messages(raw: str) -> list[BaseMessage]:
    items = json.loads(raw)
    result = []
    for item in items:
        if item["type"] == "HumanMessage":
            result.append(HumanMessage(content=item["content"]))
        elif item["type"] == "AIMessage":
            result.append(AIMessage(content=item["content"]))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Default state
# ─────────────────────────────────────────────────────────────────────────────

def _default_state() -> dict:
    return {
        "destination": None,
        "checkin": None,
        "checkout": None,
        "guests": None,
        "budget_per_night": None,
        "preferences": [],
        "trip_type": None,
        "confirmed_hotel_id": None,
        "confirmed_hotel_name": None,
        "inventory_source": None,      # "amadeus" | "liteapi" | "local"
        "errors_shown": [],            # ex: ["no_hotels_olinda"]
        "phase": "collecting",         # collecting | presenting | confirmed
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_history(user_id: str) -> list[BaseMessage]:
    r = _get_redis()
    if r:
        try:
            raw = r.get(f"hist:{user_id}")
            if raw:
                return _deserialize_messages(raw)
            return []
        except Exception as e:
            logger.warning("Redis load_history failed: %s", e)

    # In-memory fallback
    entry = _history_store.get(user_id)
    if not entry:
        return []
    messages, ts = entry
    if time.monotonic() - ts > _TTL:
        del _history_store[user_id]
        return []
    return messages


def save_history(user_id: str, messages: list[BaseMessage]) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(f"hist:{user_id}", _TTL, _serialize_messages(messages))
            return
        except Exception as e:
            logger.warning("Redis save_history failed: %s", e)

    _history_store[user_id] = (messages, time.monotonic())


def load_state(user_id: str) -> dict:
    r = _get_redis()
    if r:
        try:
            raw = r.get(f"state:{user_id}")
            if raw:
                state = json.loads(raw)
                # Ensure all default keys are present (schema evolution)
                defaults = _default_state()
                for k, v in defaults.items():
                    if k not in state:
                        state[k] = v
                return state
            return _default_state()
        except Exception as e:
            logger.warning("Redis load_state failed: %s", e)

    entry = _state_store.get(user_id)
    if not entry:
        return _default_state()
    state, ts = entry
    if time.monotonic() - ts > _TTL:
        del _state_store[user_id]
        return _default_state()
    return state


def save_state(user_id: str, state: dict) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(f"state:{user_id}", _TTL, json.dumps(state, ensure_ascii=False))
            return
        except Exception as e:
            logger.warning("Redis save_state failed: %s", e)

    _state_store[user_id] = (state, time.monotonic())


def clear_session(user_id: str) -> None:
    r = _get_redis()
    if r:
        try:
            r.delete(f"hist:{user_id}", f"state:{user_id}")
            return
        except Exception as e:
            logger.warning("Redis clear_session failed: %s", e)

    _history_store.pop(user_id, None)
    _state_store.pop(user_id, None)
