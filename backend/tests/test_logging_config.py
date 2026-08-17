import json
import logging

from app.core.logging_config import JsonFormatter, request_id_ctx_var


def test_json_formatter_produces_valid_json_with_expected_fields():
    record = logging.LogRecord(
        name="app.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="something happened", args=(), exc_info=None,
    )
    record.company_id = "acme_corp"  # simulates logger.info(..., extra={...})

    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["message"] == "something happened"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["company_id"] == "acme_corp"
    assert "timestamp" in payload


def test_json_formatter_tags_records_with_current_request_id():
    token = request_id_ctx_var.set("req-123")
    try:
        record = logging.LogRecord(
            name="app.test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="tagged", args=(), exc_info=None,
        )
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx_var.reset(token)

    assert payload["request_id"] == "req-123"


def test_json_formatter_includes_exception_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="app.test", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in payload["exception"]
