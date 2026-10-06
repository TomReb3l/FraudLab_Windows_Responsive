from fastapi.testclient import TestClient

import backend.ai_session as ai_session
from backend.llm_engine import LlmStatus
from backend.main import app

client = TestClient(app)


class _FakeLegacyLlm:
    def status(self):
        return LlmStatus(
            provider="fake",
            available=True,
            model="fake",
            endpoint="local",
            detail="ready",
        )

    def rewrite_reply(self, **kwargs):
        raise AssertionError(
            "v0.4.3 live path must not call legacy naturalizer"
        )


def test_llm_status_endpoint_is_kept_for_diagnostics(monkeypatch):
    monkeypatch.setattr(
        ai_session,
        "llm_provider",
        _FakeLegacyLlm(),
    )
    response = client.get("/api/ai/llm/status")
    assert response.status_code == 200
    assert response.json()["available"] is True


def test_nonterminal_turn_uses_approved_response_not_legacy_llm(monkeypatch):
    monkeypatch.setattr(
        ai_session,
        "llm_provider",
        _FakeLegacyLlm(),
    )

    started = client.post(
        "/api/ai/session/start",
        json={},
    ).json()

    response = client.post(
        f"/api/ai/session/{started['session_id']}/turn",
        json={"text": "Πού είσαι;"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["terminal"] is False
    assert body["generation_mode"] == "approved_response"
    assert body["response_policy"] == "approved_only"
    assert body["semantic_route"]["topic"] == "location"
    assert body["semantic_route"]["source"] == "rules"
    assert body["response_source"]["source"] == "approved_bank"


def test_terminal_turn_bypasses_semantic_router(monkeypatch):
    class _ExplodingRouter:
        def route(self, *args, **kwargs):
            raise AssertionError(
                "terminal verification must bypass semantic router"
            )

        def status(self):
            raise AssertionError("status not needed")

    monkeypatch.setattr(
        ai_session,
        "semantic_router",
        _ExplodingRouter(),
    )

    started = client.post(
        "/api/ai/session/start",
        json={},
    ).json()

    response = client.post(
        f"/api/ai/session/{started['session_id']}/turn",
        json={
            "text": "Θα κλείσω και θα σε καλέσω εγώ."
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["terminal"] is True
    assert body["generation_mode"] == "deterministic_terminal"
    assert body["semantic_route"]["topic"] == "terminal_bypass"
