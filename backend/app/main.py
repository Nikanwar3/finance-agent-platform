import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from .api.routes import router as api_router, manager
from .core.config import settings
from .core.exceptions import register_exception_handlers
from .core.logging_config import setup_logging
from .core.middleware import RequestContextMiddleware
from .core.rate_limit import limiter
from .models.database import engine, Base, SessionLocal
from .models.domain import Company
from .services.pubsub_relay import start_pubsub_relay

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

def seed_database():
    db = SessionLocal()
    # Check if we already seeded
    if db.query(Company).first():
        db.close()
        return

    seed_file = "data/company_metadata.json"
    if os.path.exists(seed_file):
        with open(seed_file, "r") as f:
            companies = json.load(f)
            for c in companies:
                db_company = Company(
                    id=c["id"],
                    name=c["name"],
                    industry=c["industry"],
                    revenue_annual=c["revenue_annual"],
                    employees=c["employees"]
                )
                db.add(db_company)
        db.commit()
        logger.info("database_seeded")
    else:
        logger.warning("seed_file_not_found", extra={"seed_file": seed_file})
    db.close()

seed_database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Relays close-workflow progress events published by the Celery worker
    # (over Redis pub/sub) out to this process's WebSocket connections.
    start_pubsub_relay(asyncio.get_event_loop(), manager)
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.state.limiter = limiter
register_exception_handlers(app)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"message": f"{settings.PROJECT_NAME} API", "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness/readiness probe target for load balancers and container
    orchestrators (ECS/K8s)."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
