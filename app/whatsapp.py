import os
from typing import Optional

import httpx

EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "hospedai")


async def send_message(to: str, text: str) -> dict:
    """Send a text message via Evolution API."""
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}
    payload = {"number": to, "text": text, "delay": 1200}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def send_typing(to: str, duration_ms: int = 2000) -> None:
    """Show typing indicator (best-effort, non-critical)."""
    url = f"{EVOLUTION_URL}/chat/sendPresence/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}
    payload = {"number": to, "presence": "composing", "delay": duration_ms}
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
        if not remote_jid or "@g.us" in remote_jid:  # ignore groups
            return None

        message = data.get("message", {})
        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        if not text:
            return None

        user_id = remote_jid.split("@")[0]
        return user_id, text

    except Exception:
        return None
