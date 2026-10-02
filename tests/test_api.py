from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_call_scenario_endpoint():
    response = client.get("/api/scenarios/call_account_security_001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "fraud_call"
    assert payload["start_node"] in payload["nodes"]


def test_unknown_scenario_is_404():
    response = client.get("/api/scenarios/does-not-exist")
    assert response.status_code == 404


def test_frontend_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "FRAUD LAB" in response.text
