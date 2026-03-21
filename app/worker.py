"""Background queue worker — consumes Redis queue and dispatches to _process().

Runs as a long-lived asyncio task inside the same Cloud Run process.
Uses run_in_executor for the blocking Redis BLPOP call so it doesn't
block the FastAPI event loop.

If Redis is unavailable the worker exits immediately (no-op); the webhook
handler falls back to FastAPI BackgroundTasks in that case.
"""

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


async def run_worker(process_fn: Callable[[str, str], Awaitable[None]]) -> None:
    """Consume messages from the Redis queue and call process_fn for each."""
    from .queue import dequeue
    from .session import _get_redis

    if not _get_redis():
        logger.info("Queue worker: Redis unavailable — worker not started")
        return

    logger.info("Queue worker started")
    loop = asyncio.get_event_loop()

    while True:
        try:
            job = await loop.run_in_executor(None, lambda: dequeue(5))
            if job:
                logger.info(
                    "Queue: dispatching job %s for user %s (queue depth check skipped)",
                    job.get("id"), job.get("user_id"),
                )
                asyncio.create_task(process_fn(job["user_id"], job["text"]))
        except asyncio.CancelledError:
            logger.info("Queue worker stopped")
            return
        except Exception as e:
            logger.error("Queue worker unexpected error: %s", e)
            await asyncio.sleep(1)
