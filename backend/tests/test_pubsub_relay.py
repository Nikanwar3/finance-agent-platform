"""publish_close_event (workers/tasks.py) and start_pubsub_relay
(services/pubsub_relay.py) are pure Redis pub/sub plumbing — no LLM calls, no
OpenAI — so fully testable for free. conftest.py points REDIS_URL at
localhost with no real Redis reachable, so agents/base.py's module-level
redis_client is already a MockRedis instance during the test run; the
"real Redis" branches are exercised below by monkeypatching that singleton.
"""

import asyncio
import json
import threading
import time

import app.services.pubsub_relay as pubsub_relay
import app.workers.tasks as tasks
from app.agents.base import MockRedis


def test_publish_close_event_is_a_noop_with_mock_redis():
    assert isinstance(tasks.redis_client, MockRedis)
    # Should not raise even though there's nowhere to actually deliver this.
    tasks.publish_close_event({"event": "close_started", "company_id": "acme"})


def test_publish_close_event_calls_real_redis_publish(monkeypatch):
    published = []

    class FakeRedis:
        def publish(self, channel, message):
            published.append((channel, message))

    monkeypatch.setattr(tasks, "redis_client", FakeRedis())

    tasks.publish_close_event({"event": "close_completed", "company_id": "acme"})

    assert len(published) == 1
    channel, message = published[0]
    assert channel == tasks.CLOSE_EVENTS_CHANNEL
    assert json.loads(message) == {"event": "close_completed", "company_id": "acme"}


def test_publish_close_event_swallows_publish_errors(monkeypatch):
    class FailingRedis:
        def publish(self, channel, message):
            raise ConnectionError("redis is down")

    monkeypatch.setattr(tasks, "redis_client", FailingRedis())

    # A pub/sub notification failing must never take down the close task itself.
    tasks.publish_close_event({"event": "close_failed", "company_id": "acme"})


def test_start_pubsub_relay_returns_none_with_mock_redis():
    assert isinstance(pubsub_relay.redis_client, MockRedis)
    loop = asyncio.new_event_loop()
    try:
        thread = pubsub_relay.start_pubsub_relay(loop, manager=None)
        assert thread is None
    finally:
        loop.close()


def test_start_pubsub_relay_broadcasts_real_redis_messages(monkeypatch):
    class FakePubSub:
        def __init__(self, messages):
            self._messages = messages

        def subscribe(self, channel):
            pass

        def listen(self):
            yield from self._messages

    class FakeRedis:
        def __init__(self, messages):
            self._messages = messages

        def pubsub(self):
            return FakePubSub(self._messages)

    broadcasted = []

    class FakeManager:
        async def broadcast(self, text):
            broadcasted.append(text)

    fake_messages = [
        {"type": "subscribe", "data": 1},  # not a "message" — must be skipped
        {"type": "message", "data": b"close_started:acme"},  # bytes, needs decoding
        {"type": "message", "data": "close_completed:acme"},  # already str
    ]
    monkeypatch.setattr(pubsub_relay, "redis_client", FakeRedis(fake_messages))

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        relay_thread = pubsub_relay.start_pubsub_relay(loop, FakeManager())
        assert relay_thread is not None

        deadline = time.monotonic() + 2
        while len(broadcasted) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)

        assert broadcasted == ["close_started:acme", "close_completed:acme"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2)
        loop.close()
