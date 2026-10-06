# AI Station Archive — Future Feature Reference

**Status:** Archived / inactive  
**Snapshot date:** 2026-10-06  
**Current FraudLab production scope:** Telephone Fraud, SMS/Phishing, E-mail/QR only.

## Purpose

This directory preserves the experimental AI/Station-4 work that existed before the Headquarters release cleanup. It is **not part of the active FraudLab runtime**, is not imported by the backend, is not exposed by a route, and is not required by Render or the Windows exhibition build.

The archive exists only so that prior research is not lost if a separate AI project is ever approved and restarted. **Do not restore these files into production by copy/paste without a new security, privacy, architecture and test review.**

## Archive structure

- `original_tree/` contains AI-exclusive files in a directory tree that mirrors their former repository locations.
- `integration_reference/` contains read-only snapshots of shared files that previously contained AI wiring. These are reference material only; they must **not** replace the current production files wholesale.
- `MANIFEST.json` records original paths and SHA-256 hashes for traceability.

## Original location map

| Archived file | Former repository location |
|---|---|
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/__init__.py` | `backend/ai_agent/__init__.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/fraudster_agent.py` | `backend/ai_agent/fraudster_agent.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/guardrails.py` | `backend/ai_agent/guardrails.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/memory.py` | `backend/ai_agent/memory.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/persona.py` | `backend/ai_agent/persona.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_agent/strategy.py` | `backend/ai_agent/strategy.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_scenario_engine.py` | `backend/ai_scenario_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/ai_session.py` | `backend/ai_session.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/approved_response_engine.py` | `backend/approved_response_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/llm_engine.py` | `backend/llm_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/semantic_router.py` | `backend/semantic_router.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/stt_engine.py` | `backend/stt_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/backend/tts_engine.py` | `backend/tts_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/data/ai_fallback_corpus_v044.json` | `data/ai_fallback_corpus_v044.json` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/data/ai_fallback_corpus_v046.json` | `data/ai_fallback_corpus_v046.json` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/data/ai_scenarios.json` | `data/ai_scenarios.json` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/docs/STATION4_V041.md` | `docs/STATION4_V041.md` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/docs/STATION4_V042.md` | `docs/STATION4_V042.md` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/docs/STATION4_V043.md` | `docs/STATION4_V043.md` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/docs/STATION4_V044.md` | `docs/STATION4_V044.md` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/frontend/ai/index.html` | `frontend/ai/index.html` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/static/css/ai.css` | `static/css/ai.css` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/static/js/ai.js` | `static/js/ai.js` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_fallback_v044.py` | `tests/test_ai_fallback_v044.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_llm_api.py` | `tests/test_ai_llm_api.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_llm_v041.py` | `tests/test_ai_llm_v041.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_quality_v042.py` | `tests/test_ai_quality_v042.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_router_v043.py` | `tests/test_ai_router_v043.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_station.py` | `tests/test_ai_station.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_stt_api.py` | `tests/test_ai_stt_api.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_ai_tts_api.py` | `tests/test_ai_tts_api.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_llm_engine.py` | `tests/test_llm_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_stt_engine.py` | `tests/test_stt_engine.py` |
| `FUTURE_FEATURES/AI_STATION_ARCHIVE/original_tree/tests/test_tts_engine.py` | `tests/test_tts_engine.py` |

## Shared integration points retained as reference

The following pre-cleanup snapshots are stored under `integration_reference/`:

- `backend/main.py` — former conditional AI router and `/ai` page wiring.
- `backend/config.py` — former `ENABLE_AI` configuration flag.
- `render.yaml` — former Render `ENABLE_AI=false` environment setting.
- `scripts/exhibition_launcher.py` — former launcher checks for the AI-disabled state.
- `scripts/validate_exhibition.py` — former validator checks for the AI-disabled state.

These files contain other production logic as well. If AI development is restarted, use them **only as historical diff/reference material** and re-integrate the required pieces deliberately into the then-current source tree.

## If AI development is restarted

Treat it as a new, separately approved workstream. Recommended order:

1. Create a dedicated branch or separate repository for the AI work.
2. Review the archived architecture before restoring any module.
3. Decide which components are still required: scenario engine, semantic routing, local LLM/Ollama, local STT/Whisper, TTS, approved-response layer, or none of them.
4. Restore only the files that are actually required, using the table above for their former locations.
5. Recreate the integration with the **current** `backend/main.py` and `backend/config.py`; do not overwrite them with archived snapshots.
6. Reassess dependencies, local model distribution, hardware requirements, licensing, data protection, logging, microphone permissions and threat model.
7. Add a new feature flag only if there is a concrete operational requirement.
8. Rebuild and update tests before exposing any new route or UI element.
9. Run the complete deterministic FraudLab regression suite to prove Telephone, SMS and QR remain unaffected.
10. Perform a new institutional/security review before merging AI functionality into an exhibition release.

## Current production rule

The active FraudLab repository must remain fully functional if this entire `FUTURE_FEATURES/AI_STATION_ARCHIVE/` directory is deleted. Nothing in production may import from or depend on this archive.
