"""Domain-specific exceptions and their FastAPI handlers.

Every error the API returns — expected (404s, conflicts) or unexpected
(bugs, DB outages) — comes back as the same JSON envelope:

    {"error": {"code": "COMPANY_NOT_FOUND", "message": "..."}, "request_id": "..."}

so API consumers never have to branch on response shape by status code.
"""
import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded

from .logging_config import request_id_ctx_var

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "APP_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CompanyNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "COMPANY_NOT_FOUND"

    def __init__(self, company_id: str):
        super().__init__(f"Company '{company_id}' was not found.")


class CloseAlreadyInProgressError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CLOSE_ALREADY_IN_PROGRESS"

    def __init__(self, company_id: str):
        super().__init__(f"A close is already running for company '{company_id}'.")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message},
            "request_id": request_id_ctx_var.get(),
        },
    )


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return _error_response(exc.status_code, exc.error_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        logger.warning("request_validation_failed", extra={"errors": exc.errors()})
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "The request could not be validated.",
        )

    @app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
        return _error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMITED",
            f"Rate limit exceeded: {exc.detail}",
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, exc: SQLAlchemyError):
        logger.exception("database_error")
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "DATABASE_ERROR",
            "A database error occurred. Please try again.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("unhandled_exception")
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )
