# STATION4_RESEARCH_FALLBACK_V044
# STATION4_SEMANTIC_ROUTER_V043
# STATION4_LLM_V041
# STATION4_LLM_V04
# STATION4_TTS_V03
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.ai_scenario_engine import (
    AiScenarioEngine,
    AiScenarioNotFound,
    AiSessionNotFound,
    AiSessionStore,
)
from backend.approved_response_engine import (
    ApprovedResponseEngine,
    ApprovedResponseError,
)
from backend.semantic_router import create_semantic_router
from backend.stt_engine import (
    MAX_AUDIO_BYTES,
    SttAudioError,
    SttError,
    SttUnavailableError,
    create_stt_provider,
)
from backend.tts_engine import (
    MAX_TTS_CHARS,
    TtsError,
    TtsInputError,
    TtsUnavailableError,
    create_tts_provider,
)
from backend.llm_engine import create_llm_provider

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "ai_scenarios.json"
CORPUS_FILE = BASE_DIR / "data" / "ai_fallback_corpus_v044.json"

engine = AiScenarioEngine(DATA_FILE)
sessions = AiSessionStore(engine=engine, ttl_seconds=600)
approved_responses = ApprovedResponseEngine(engine, CORPUS_FILE)
semantic_router = create_semantic_router()
stt_provider = create_stt_provider(BASE_DIR)
tts_provider = create_tts_provider(BASE_DIR)

# Kept only for the existing /llm/status diagnostics and future GPU
# experimentation. v0.4.3 does NOT pass rewrite_reply() output to visitors.
llm_provider = create_llm_provider()

router = APIRouter(prefix="/api/ai", tags=["station-4"])


class StartRequest(BaseModel):
    scenario_id: str | None = None


class TurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=280)


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)


@router.get("/stt/status")
def stt_status() -> dict:
    return stt_provider.status().as_dict()


@router.post("/stt/transcribe")
async def stt_transcribe(request: Request) -> dict:
    status = stt_provider.status()
    if not status.available:
        raise HTTPException(status_code=503, detail=status.detail)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_AUDIO_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Audio payload too large",
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length",
            )

    audio_bytes = await request.body()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio payload too large",
        )
    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty audio payload",
        )

    duration_ms: int | None = None
    raw_duration = request.headers.get("x-audio-duration-ms")
    if raw_duration:
        try:
            duration_ms = max(
                0,
                min(60000, int(raw_duration)),
            )
        except ValueError:
            duration_ms = None

    try:
        return stt_provider.transcribe(
            audio_bytes,
            content_type=request.headers.get(
                "content-type",
                "application/octet-stream",
            ),
            duration_ms=duration_ms,
        )
    except SttUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except SttAudioError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except SttError as exc:
        raise HTTPException(
            status_code=500,
            detail="Local speech recognition failed",
        ) from exc


@router.get("/tts/status")
def tts_status() -> dict:
    return tts_provider.status().as_dict()


@router.post("/tts/synthesize")
def tts_synthesize(payload: TtsRequest) -> Response:
    status = tts_provider.status()
    if not status.available:
        raise HTTPException(
            status_code=503,
            detail=status.detail,
        )

    try:
        wav_bytes = tts_provider.synthesize(payload.text)
    except TtsUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except TtsInputError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except TtsError as exc:
        raise HTTPException(
            status_code=500,
            detail="Local speech synthesis failed",
        ) from exc

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/llm/status")
def llm_status() -> dict:
    return llm_provider.status().as_dict()


@router.get("/router/status")
def semantic_router_status() -> dict:
    status = semantic_router.status().as_dict()
    status["policy"] = "rules_first_then_local_llm_enum_only"
    status["visitor_facing_generation"] = False
    return status


@router.get("/corpus/status")
def corpus_status() -> dict:
    return approved_responses.status()


@router.get("/scenario")
def get_default_scenario() -> dict:
    return engine.public_scenario()


@router.post("/session/start")
def start_session(
    payload: StartRequest | None = None,
) -> dict:
    try:
        session_id, state, scenario = sessions.start(
            payload.scenario_id if payload else None
        )
    except AiScenarioNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="AI scenario not found",
        ) from exc

    return {
        "session_id": session_id,
        "scenario": scenario,
        "assistant_text": scenario["opening"],
        "stage": state.stage,
        "turn": state.turn,
        "score": state.score,
        "terminal": False,
        "generation_mode": "approved_opening",
        "response_policy": "approved_only",
    }


@router.post("/session/{session_id}/turn")
def session_turn(
    session_id: str,
    payload: TurnRequest,
) -> dict:
    try:
        snapshot = sessions.llm_snapshot(session_id)
        result = sessions.turn(
            session_id,
            payload.text,
        )
    except AiSessionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="AI session not found",
        ) from exc

    # Score, stage, broad intent and terminal outcomes are always decided by
    # the deterministic scenario engine before semantic routing.
    if result.get("terminal"):
        result["generation_mode"] = "deterministic_terminal"
        result["response_policy"] = "deterministic_terminal"
        result["corpus_version"] = "0.4.4"
        result["semantic_route"] = {
            "topic": "terminal_bypass",
            "confidence": 1.0,
            "source": "deterministic_engine",
        }
        result["router_metrics"] = {}
        result["llm_metrics"] = {}
        result["llm_context_turns"] = 0
        return result

    scenario_id = str(snapshot["scenario_id"])
    reply_stage = str(
        result.get("reply_stage")
        or snapshot.get("stage")
        or result.get("stage")
        or ""
    )

    canonical_reply = str(result["assistant_text"])
    allowed_topics = approved_responses.allowed_topics(
        scenario_id,
        reply_stage,
    )

    semantic_route = semantic_router.route(
        payload.text,
        allowed_topics=allowed_topics,
        stage=reply_stage,
        deterministic_intent=str(
            result.get("intent", "default")
        ),
    )

    try:
        approved = approved_responses.select(
            scenario_id=scenario_id,
            stage_id=reply_stage,
            topic=semantic_route.topic,
            deterministic_intent=str(
                result.get("intent", "default")
            ),
            visitor_text=payload.text,
            turn=int(result.get("turn", 0)),
            canonical_reply=canonical_reply,
        )
    except ApprovedResponseError:
        # Fail closed: even a data/configuration mistake cannot turn into
        # free model generation. The deterministic canonical reply remains.
        result["assistant_text"] = canonical_reply
        result["generation_mode"] = "deterministic_fallback"
        meta = approved_responses.stage_metadata(reply_stage)
        result["response_source"] = {
            "topic": "canonical",
            "source": "deterministic_canonical",
            "variant": 0,
            "response_id": "canonical",
            "role": meta["role"],
            "speaker_label": meta["speaker_label"],
            "role_handoff": False,
        }
        result["speaker_role"] = meta["role"]
        result["speaker_label"] = meta["speaker_label"]
        result["role_handoff"] = False
    else:
        result["assistant_text"] = approved.text
        result["generation_mode"] = "approved_response"
        result["response_source"] = approved.as_dict()
        result["speaker_role"] = approved.role
        result["speaker_label"] = approved.speaker_label
        result["role_handoff"] = approved.role_handoff

    result["response_policy"] = "approved_only"
    result["response_corpus"] = "research_fallback_corpus_v044"
    result["corpus_version"] = "0.4.4"
    result["semantic_route"] = semantic_route.as_dict()
    result["router_metrics"] = dict(
        semantic_route.metrics or {}
    )

    # Compatibility field for existing diagnostics. In v0.4.3 this contains
    # router timing only; no visitor-facing text is generated by the LLM.
    result["llm_metrics"] = dict(
        semantic_route.metrics or {}
    )
    result["llm_context_turns"] = 0

    return result


@router.delete("/session/{session_id}")
def end_session(
    session_id: str,
) -> dict[str, bool]:
    return {"ended": sessions.end(session_id)}
