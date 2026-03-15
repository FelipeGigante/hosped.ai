"""In-memory session store with TTL. No external dependencies — good enough for MVP."""

import time
from langchain_core.messages import BaseMessage

_TTL = 86400.0  # 24h in seconds
_store: dict[str, tuple[list[BaseMessage], float]] = {}


def load_history(user_id: str) -> list[BaseMessage]:
    entry = _store.get(user_id)
    if not entry:
        return []
    messages, ts = entry
    if time.monotonic() - ts > _TTL:
        del _store[user_id]
        return []
    return messages


def save_history(user_id: str, messages: list[BaseMessage]) -> None:
    _store[user_id] = (messages, time.monotonic())


def clear_history(user_id: str) -> None:
    _store.pop(user_id, None)
