"""In-memory session store with TTL. No external dependencies — good enough for MVP."""

import time
from langchain_core.messages import BaseMessage

_TTL = 86400.0  # 24h in seconds

_history_store: dict[str, tuple[list[BaseMessage], float]] = {}
_state_store: dict[str, tuple[dict, float]] = {}


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
        "errors_shown": [],   # e.g. ["no_hotels_recife"] — prevents repeated error msgs
        "phase": "collecting",  # collecting | presenting | confirmed
    }


def load_history(user_id: str) -> list[BaseMessage]:
    entry = _history_store.get(user_id)
    if not entry:
        return []
    messages, ts = entry
    if time.monotonic() - ts > _TTL:
        del _history_store[user_id]
        return []
    return messages


def save_history(user_id: str, messages: list[BaseMessage]) -> None:
    _history_store[user_id] = (messages, time.monotonic())


def load_state(user_id: str) -> dict:
    entry = _state_store.get(user_id)
    if not entry:
        return _default_state()
    state, ts = entry
    if time.monotonic() - ts > _TTL:
        del _state_store[user_id]
        return _default_state()
    return state


def save_state(user_id: str, state: dict) -> None:
    _state_store[user_id] = (state, time.monotonic())


def clear_history(user_id: str) -> None:
    _history_store.pop(user_id, None)
    _state_store.pop(user_id, None)
