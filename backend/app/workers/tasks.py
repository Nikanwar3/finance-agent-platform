"""Celery tasks — the actual background-worker execution of the month-end
close, decoupled from the request/response cycle of the API.

``POST /api/close/{company_id}`` only enqueues ``run_company_close_task`` and
returns immediately; a separate ``worker`` process (see docker-compose.yml)
pulls it off the Redis-backed queue and runs it. Progress/completion events
are published to Redis pub/sub so the API process's WebSocket connections
can relay them to the frontend without polling the DB.
"""
import json
import logging

from ..agents.agent_workflows import OrchestratorAgent
from ..agents.base import redis_client, MockRedis
from ..core.celery_app import celery_app
from ..models.database import SessionLocal

logger = logging.getLogger(__name__)

CLOSE_EVENTS_CHANNEL = "close_events"

# One orchestrator per worker process — its sub-agents are stateless aside
# from the shared Redis memory, so it's safe to reuse across tasks.
_orchestrator = OrchestratorAgent()


def publish_close_event(payload: dict) -> None:
    if isinstance(redis_client, MockRedis):
        # No real Redis available (local dev without Docker) — there's no
        # cross-process pub/sub to relay to, so just skip it.
        return
    try:
        redis_client.publish(CLOSE_EVENTS_CHANNEL, json.dumps(payload))
    except Exception:
        logger.warning("failed_to_publish_close_event", exc_info=True, extra={"payload": payload})


@celery_app.task(name="app.workers.tasks.run_company_close_task", bind=True, max_retries=2)
def run_company_close_task(self, company_id: str):
    logger.info("close_task_started", extra={"company_id": company_id})
    publish_close_event({"event": "close_started", "company_id": company_id})

    db = SessionLocal()
    try:
        success = _orchestrator.run_company_close(company_id, db)
        publish_close_event({
            "event": "close_completed" if success else "close_failed",
            "company_id": company_id,
        })
        logger.info("close_task_finished", extra={"company_id": company_id, "success": success})
        return {"company_id": company_id, "success": success}
    except Exception as exc:
        logger.exception("close_task_failed", extra={"company_id": company_id})
        publish_close_event({"event": "close_failed", "company_id": company_id, "error": str(exc)})
        raise
    finally:
        db.close()
