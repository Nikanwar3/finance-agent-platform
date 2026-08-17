"""Bridges Redis pub/sub (published by the Celery worker process) to this
API process's in-memory WebSocket connections.

redis-py's pub/sub API is blocking, so it runs on a dedicated background
thread; each message it receives is handed back to the FastAPI event loop
via ``run_coroutine_threadsafe`` so it can be broadcast over the async
WebSocket connections.
"""
import asyncio
import logging
import threading

from ..agents.base import redis_client, MockRedis
from ..workers.tasks import CLOSE_EVENTS_CHANNEL

logger = logging.getLogger(__name__)


def start_pubsub_relay(loop: asyncio.AbstractEventLoop, manager) -> threading.Thread | None:
    if isinstance(redis_client, MockRedis):
        logger.info("pubsub_relay_disabled", extra={"reason": "MockRedis fallback in use"})
        return None

    def _listen():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(CLOSE_EVENTS_CHANNEL)
        logger.info("pubsub_relay_started", extra={"channel": CLOSE_EVENTS_CHANNEL})
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message["data"]
            text = data.decode() if isinstance(data, bytes) else data
            asyncio.run_coroutine_threadsafe(manager.broadcast(text), loop)

    thread = threading.Thread(target=_listen, name="redis-pubsub-relay", daemon=True)
    thread.start()
    return thread
