"""Redis-based message queue for reliable async processing.

Uses Redis LIST (RPUSH / BLPOP) as a FIFO queue.
Falls back gracefully to None when Redis is unavailable —
callers should use BackgroundTasks as fallback in that case.
"""

import json
import logging
import time
import uuid

logger = logging.getLogger(__name__)

QUEUE_KEY = "msg:queue"


def enqueue(user_id: str, text: str) -> bool:
    """Push a message onto the queue. Returns True if enqueued, False if Redis unavailable."""
    from .session import _get_redis
    r = _get_redis()
    if not r:
        return False
    job = {
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "text": text,
        "ts": time.time(),
    }
    try:
        r.rpush(QUEUE_KEY, json.dumps(job, ensure_ascii=False))
        logger.debug("Enqueued job %s for %s", job["id"], user_id)
        return True
    except Exception as e:
        logger.warning("Queue enqueue failed: %s", e)
        return False


def dequeue(timeout: int = 5) -> dict | None:
    """Block up to `timeout` seconds for a message. Returns parsed dict or None."""
    from .session import _get_redis
    r = _get_redis()
    if not r:
        return None
    try:
        result = r.blpop(QUEUE_KEY, timeout=timeout)
        if result:
            _, raw = result
            return json.loads(raw)
    except Exception as e:
        logger.warning("Queue dequeue failed: %s", e)
    return None


def queue_length() -> int:
    """Return current queue depth (for monitoring)."""
    from .session import _get_redis
    r = _get_redis()
    if not r:
        return 0
    try:
        return r.llen(QUEUE_KEY)
    except Exception:
        return 0
