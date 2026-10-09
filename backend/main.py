from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.scenario_engine import ScenarioEngine


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = BASE_DIR / "data" / "call_scenarios.json"
SMS_DATA_FILE = BASE_DIR / "data" / "sms_scenarios.json"
QR_DATA_FILE = BASE_DIR / "data" / "qr_scenarios.json"
VIBER_DATA_FILE = BASE_DIR / "data" / "viber_takeover_scenario.json"

FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = BASE_DIR / "static"


engine = ScenarioEngine(DATA_FILE)


app = FastAPI(
    title="FRAUD LAB – Fraud Exhibition System",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "offline-first",
    }


@app.get("/api/scenarios")
def list_scenarios():
    return JSONResponse(
        content=engine.list_scenarios(),
        media_type="application/json; charset=utf-8"
    )


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    try:
        return engine.get_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sms-challenge")
def get_sms_challenge() -> dict:
    try:
        return json.loads(
            SMS_DATA_FILE.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="SMS challenge data unavailable",
        ) from exc


@app.get("/api/viber-scenario")
def get_viber_scenario() -> dict:
    try:
        return json.loads(VIBER_DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Viber scenario data unavailable") from exc


@app.get("/api/qr-challenge")
def get_qr_challenge() -> dict:
    try:
        return json.loads(
            QR_DATA_FILE.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="QR challenge data unavailable",
        ) from exc


@app.get("/")
def root() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "home" / "index.html"
    )


@app.get("/call")
def call_booth() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "call" / "index.html"
    )


@app.get("/sms")
def sms_challenge_page() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "sms" / "index.html"
    )


@app.get("/qr")
def qr_challenge_page() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "qr" / "index.html"
    )

@app.get("/viber")
def viber_station_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "viber" / "index.html")


CALL_AUDIO_MANIFEST_FILE = BASE_DIR / "data" / "call_audio_manifest.json"


@app.get("/api/call-audio-manifest")
def get_call_audio_manifest() -> dict:
    try:
        return json.loads(
            CALL_AUDIO_MANIFEST_FILE.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Call audio manifest unavailable",
        ) from exc