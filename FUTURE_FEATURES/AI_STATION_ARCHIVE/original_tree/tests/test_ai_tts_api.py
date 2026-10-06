from fastapi.testclient import TestClient

import backend.ai_session as ai_session
from backend.main import app
from backend.tts_engine import TtsStatus

client = TestClient(app)


class _FakeTts:
    def status(self):
        return TtsStatus(
            provider="fake",
            available=True,
            voice="FakeGreek",
            detail="ready",
        )

    def synthesize(self, text: str):
        assert text == "Καλημέρα."
        return b"RIFF" + b"0" * 128


def test_tts_status_endpoint(monkeypatch):
    monkeypatch.setattr(ai_session, "tts_provider", _FakeTts())
    response = client.get("/api/ai/tts/status")
    assert response.status_code == 200
    assert response.json()["voice"] == "FakeGreek"


def test_tts_synthesize_endpoint(monkeypatch):
    monkeypatch.setattr(ai_session, "tts_provider", _FakeTts())
    response = client.post("/api/ai/tts/synthesize", json={"text": "Καλημέρα."})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.content.startswith(b"RIFF")
