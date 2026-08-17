import os

# Must be set before `app.main` (and anything it imports) is loaded, since
# the DB engine and Redis client are both constructed at import time.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_finance.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")  # -> MockRedis fallback
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("AWS_S3_BUCKET", "")

import json

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import limiter
from app.main import app
from app.models.database import Base, SessionLocal, engine
from app.models.domain import Company


@pytest.fixture(autouse=True)
def _clean_database():
    """Reset to a known-seeded state before every test so tests don't leak
    state (e.g. a company left `in_progress`, or rate-limit counters) into
    one another."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter.reset()

    db = SessionLocal()
    with open("data/company_metadata.json") as f:
        for c in json.load(f):
            db.add(Company(
                id=c["id"],
                name=c["name"],
                industry=c["industry"],
                revenue_annual=c["revenue_annual"],
                employees=c["employees"],
            ))
    db.commit()
    db.close()

    yield


@pytest.fixture
def client():
    # raise_server_exceptions=False so tests can assert on the 500 response
    # our own `Exception` handler produces, instead of the client re-raising
    # the original error for interactive debugging.
    return TestClient(app, raise_server_exceptions=False)
