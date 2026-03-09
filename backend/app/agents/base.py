from agno.agent import Agent
from agno.models.openai import OpenAIChat
from ..core.config import settings
import redis
import json

# Define the shared redis connection
def get_redis_client():
    if "localhost" in settings.REDIS_URL:
        # Fallback to in-process memory dict for local dev if redis isn't installed
        return MockRedis()
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return r
    except Exception:
        return MockRedis()

class MockRedis:
    _store = {}
    def set(self, key, value):
        self._store[key] = value
    def get(self, key):
        return self._store.get(key)
    def delete(self, key):
        if key in self._store:
            del self._store[key]

redis_client = get_redis_client()

def get_shared_memory(key_prefix: str, company_id: str):
    key = f"{key_prefix}:{company_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return {}

def set_shared_memory(key_prefix: str, company_id: str, data: dict):
    key = f"{key_prefix}:{company_id}"
    # Merge with existing
    existing = get_shared_memory(key_prefix, company_id)
    existing.update(data)
    redis_client.set(key, json.dumps(existing))

def create_base_agent(name: str, instructions: str) -> Agent:
    return Agent(
        name=name,
        model=OpenAIChat(id="gpt-4o-mini", api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else OpenAIChat(id="gpt-4o-mini", api_key="dummy"),
        instructions=instructions,
        markdown=True
    )
