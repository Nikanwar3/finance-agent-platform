from app.models.database import SessionLocal
from app.models.domain import Company


def _first_company_id():
    db = SessionLocal()
    company_id = db.query(Company).first().id
    db.close()
    return company_id


def test_close_unknown_company_returns_404(client):
    response = client.post("/api/close/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPANY_NOT_FOUND"


def test_close_enqueues_celery_task_without_blocking(client, monkeypatch):
    """The endpoint should hand off to Celery and return immediately —
    it must NOT run the (slow, multi-agent) orchestration inline."""
    calls = []
    monkeypatch.setattr(
        "app.api.routes.run_company_close_task.delay",
        lambda company_id: calls.append(company_id),
    )

    company_id = _first_company_id()
    response = client.post(f"/api/close/{company_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Close process queued"
    assert calls == [company_id]


def test_close_already_in_progress_returns_409(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.run_company_close_task.delay", lambda company_id: None)

    company_id = _first_company_id()
    db = SessionLocal()
    company = db.query(Company).filter(Company.id == company_id).first()
    company.status = "in_progress"
    db.commit()
    db.close()

    response = client.post(f"/api/close/{company_id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLOSE_ALREADY_IN_PROGRESS"
