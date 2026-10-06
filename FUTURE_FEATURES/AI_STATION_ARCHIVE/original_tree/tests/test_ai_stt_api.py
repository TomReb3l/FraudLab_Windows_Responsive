from __future__ import annotations

from fastapi.testclient import TestClient

import backend.ai_session as ai_session
from backend.main import app
from backend.stt_engine import SttStatus

client = TestClient(app)


class _FakeStt:
    def status(self):
        return SttStatus(
            provider="fake",
            available=True,
            language="el",
            model="fake.bin",
            detail="ready",
        )

    def transcribe(self, audio_bytes, *, content_type, duration_ms=None):
        assert audio_bytes == b"voice"
        assert content_type.startswith("audio/webm")
        return {
            "text": "Θα σε καλέσω εγώ.",
            "provider": "fake",
            "language": "el",
            "model": "fake.bin",
            "duration_ms": duration_ms,
            "truncated": False,
        }


def test_stt_status_endpoint(monkeypatch):
    monkeypatch.setattr(ai_session, "stt_provider", _FakeStt())
    response = client.get("/api/ai/stt/status")
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["language"] == "el"


def test_stt_transcribe_endpoint_accepts_raw_audio(monkeypatch):
    monkeypatch.setattr(ai_session, "stt_provider", _FakeStt())
    response = client.post(
        "/api/ai/stt/transcribe",
        content=b"voice",
        headers={
            "Content-Type": "audio/webm;codecs=opus",
            "X-Audio-Duration-Ms": "1400",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Θα σε καλέσω εγώ."
    assert body["duration_ms"] == 1400
