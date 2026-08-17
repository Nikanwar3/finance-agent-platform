def test_list_companies_returns_seeded_companies(client):
    response = client.get("/api/companies")

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert {"id", "name", "industry", "status", "progress"} <= body[0].keys()


def test_get_company_by_id(client):
    company_id = client.get("/api/companies").json()[0]["id"]

    response = client.get(f"/api/companies/{company_id}")

    assert response.status_code == 200
    assert response.json()["id"] == company_id


def test_get_unknown_company_returns_structured_404(client):
    response = client.get("/api/companies/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "COMPANY_NOT_FOUND"
    assert "does-not-exist" in body["error"]["message"]
    assert "request_id" in body


def test_response_carries_request_id_header(client):
    response = client.get("/api/companies")

    assert "X-Request-ID" in response.headers


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
