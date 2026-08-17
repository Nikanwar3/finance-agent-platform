from app.core.exceptions import CompanyNotFoundError, CloseAlreadyInProgressError
from app.main import app
from app.models import database


def test_company_not_found_error_shape():
    err = CompanyNotFoundError("acme_corp")
    assert err.status_code == 404
    assert err.error_code == "COMPANY_NOT_FOUND"
    assert "acme_corp" in err.message


def test_close_already_in_progress_error_shape():
    err = CloseAlreadyInProgressError("acme_corp")
    assert err.status_code == 409
    assert err.error_code == "CLOSE_ALREADY_IN_PROGRESS"


def test_unhandled_exception_returns_structured_500(client):
    """Force an unexpected failure (not one of our domain AppErrors) and
    confirm it still comes back as the same JSON error envelope, with the
    real cause logged server-side rather than leaked to the client."""

    def _broken_get_db():
        raise RuntimeError("simulated unexpected failure")
        yield  # pragma: no cover - never reached, keeps this a generator

    app.dependency_overrides[database.get_db] = _broken_get_db
    try:
        response = client.get("/api/companies")
    finally:
        app.dependency_overrides.pop(database.get_db, None)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "simulated unexpected failure" not in body["error"]["message"]  # not leaked
    assert "request_id" in body


def test_unknown_route_returns_fastapi_default_404(client):
    """A route that doesn't exist at all (vs. a company that doesn't exist)
    should 404 from FastAPI's router, not from our domain error handler."""
    response = client.get("/api/this-route-does-not-exist")

    assert response.status_code == 404
