from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ai_page_is_served():
    response = client.get("/ai")
    assert response.status_code == 200
    assert "STATION 4" in response.text


def test_ai_session_can_start_and_verify_independently():
    started = client.post("/api/ai/session/start", json={})
    assert started.status_code == 200
    payload = started.json()
    assert payload["terminal"] is False
    assert payload["session_id"]

    session_id = payload["session_id"]
    result = client.post(
        f"/api/ai/session/{session_id}/turn",
        json={"text": "Θα κλείσω και θα σε καλέσω εγώ στο τηλέφωνο που ξέρω."},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["terminal"] is True
    assert body["outcome"]["id"] == "verified"
    assert body["score"] == 100


def test_ai_session_does_not_echo_arbitrary_visitor_text():
    started = client.post("/api/ai/session/start", json={}).json()
    marker = "PRIVATE-MARKER-DO-NOT-ECHO-9472"
    result = client.post(
        f"/api/ai/session/{started['session_id']}/turn",
        json={"text": marker},
    )
    assert result.status_code == 200
    assert marker not in result.text


def test_ai_session_unknown_id_is_404():
    response = client.post(
        "/api/ai/session/not-a-real-session/turn",
        json={"text": "Γεια"},
    )
    assert response.status_code == 404


def test_ai_session_can_be_deleted():
    started = client.post("/api/ai/session/start", json={}).json()
    sid = started["session_id"]
    deleted = client.delete(f"/api/ai/session/{sid}")
    assert deleted.status_code == 200
    assert deleted.json()["ended"] is True
    after = client.post(
        f"/api/ai/session/{sid}/turn",
        json={"text": "Γεια"},
    )
    assert after.status_code == 404
