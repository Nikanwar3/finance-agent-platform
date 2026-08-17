from app.api.routes import LIST_RATE_LIMIT
from app.core.rate_limit import _storage_uri


def test_limiter_falls_back_to_memory_storage_without_real_redis():
    # conftest sets REDIS_URL to a "localhost" URL, which agents/base.py
    # treats as "no real Redis available" and falls back to MockRedis — the
    # limiter should follow suit rather than trying (and failing) to reach
    # a Redis instance that isn't there.
    assert _storage_uri == "memory://"


def test_read_endpoint_returns_429_once_limit_exceeded(client):
    limit = int(LIST_RATE_LIMIT.split("/")[0])

    responses = [client.get("/api/issues") for _ in range(limit)]
    assert all(r.status_code == 200 for r in responses)

    throttled = client.get("/api/issues")

    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "RATE_LIMITED"
