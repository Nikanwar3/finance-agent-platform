from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from ..agents.base import redis_client, MockRedis

# Reuse the same Redis instance the agents use for shared memory as the
# rate-limit counter store, so limits hold across multiple uvicorn workers.
# When Redis isn't actually reachable (local dev without Docker), fall back
# to slowapi's in-memory storage rather than failing requests outright —
# mirroring the MockRedis fallback in agents/base.py.
_storage_uri = "memory://" if isinstance(redis_client, MockRedis) else settings.REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=[settings.RATE_LIMIT_READ],
)
