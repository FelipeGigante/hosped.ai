import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "hospedai")

# Dedup cache: message_id → timestamp. Prevents double-processing when
# both global and instance webhooks fire for the same event.
_seen_ids: dict[str, float] = {}
_SEEN_TTL = 60  # seconds


def _is_duplicate(message_id: str) -> bool:
    # Try Redis first — cross-instance dedup when multiple Cloud Run instances are running
    try:
        from .session import _get_redis
        r = _get_redis()
        if r:
            key = f"msg:seen:{message_id}"
            if r.exists(key):
                return True
            r.setex(key, _SEEN_TTL, "1")
            return False
    except Exception:
        pass

    # Fallback: in-memory dedup (single instance / no Redis)
    now = time.monotonic()
    expired = [k for k, t in _seen_ids.items() if now - t > _SEEN_TTL]
    for k in expired:
        del _seen_ids[k]
    if message_id in _seen_ids:
        return True
    _seen_ids[message_id] = now
    return False


def _jid_to_number(jid: str) -> str:
    """Extract plain phone number from a WhatsApp JID."""
    return jid.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("@lid", "")


async def send_message(to: str, text: str) -> dict:
    """Send a text message via Evolution API."""
    number = _jid_to_number(to)
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}
    payload = {"number": number, "text": text, "delay": 500}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 400:
            logger.error("sendText 400 for %s — response: %s", number, resp.text)
            return {"error": "send_failed", "number": number}
        resp.raise_for_status()
        return resp.json()


async def send_typing(to: str, duration_ms: int = 2000) -> None:
    """Show typing indicator (best-effort, non-critical)."""
    number = _jid_to_number(to)
    url = f"{EVOLUTION_URL}/chat/sendPresence/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}
    payload = {"number": number, "presence": "composing", "delay": duration_ms}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload, headers=headers)
    except Exception:
        pass


def parse_inbound(payload: dict) -> Optional[tuple[str, str]]:
    """Parse Evolution API webhook. Returns (user_id, text) or None if not actionable."""
    try:
        if payload.get("event") != "messages.upsert":
            return None

        data = payload.get("data", {})
        key = data.get("key", {})

        if key.get("fromMe", False):
            return None

        remote_jid = key.get("remoteJid", "")
        if not remote_jid or "@g.us" in remote_jid:
            return None

        # @lid contacts: resolve to real phone via senderPn (Evolution API v2.3+)
        if "@lid" in remote_jid:
            sender_pn = key.get("senderPn") or data.get("senderPn")
            if sender_pn:
                remote_jid = f"{sender_pn}@s.whatsapp.net"
                logger.info("Resolved @lid → %s via senderPn", remote_jid)
            else:
                logger.warning("@lid contact %s has no senderPn — ignoring message", remote_jid)
                return None

        message = data.get("message", {})
        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        if not text:
            return None

        message_id = key.get("id", "")
        if message_id and _is_duplicate(message_id):
            logger.debug("Duplicate webhook for message %s — ignoring", message_id)
            return None

        return remote_jid, text

    except Exception:
        return None
