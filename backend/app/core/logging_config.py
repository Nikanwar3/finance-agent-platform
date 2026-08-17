"""Structured (JSON) logging setup.

Every log line is emitted as a single JSON object so it can be shipped to
CloudWatch Logs / any log aggregator and queried by field instead of grepped
as free text. Each record is automatically tagged with the current request's
ID (via a contextvar set by ``RequestContextMiddleware``) so a single
request's log lines can be correlated end to end.
"""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

# Set by RequestContextMiddleware for the lifetime of a single request;
# read by JsonFormatter so every log line emitted while handling that
# request carries the same request_id without threading it through every
# function call.
request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

_RESERVED_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx_var.get(),
        }

        # Surface any custom fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger to emit structured JSON to stdout.

    Idempotent: safe to call more than once (e.g. once from the FastAPI app
    and once from the Celery worker entrypoint) without duplicating handlers.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers that log un-structured plain text.
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
