from __future__ import annotations

import json
from pathlib import Path

from backend.ai_scenario_engine import AiScenarioEngine
from backend.approved_response_engine import (
    ApprovedResponseEngine,
)
from backend.semantic_router import (
    HybridSemanticRouter,
    OllamaSemanticRouter,
    SemanticRoute,
    SemanticRouterError,
    _scrub_for_router,
    route_by_rules,
)


ROOT = Path(__file__).resolve().parents[1]


def test_common_greek_questions_route_without_llm():
    cases = {
        "Πού είσαι;": "location",
        "Έχεις χτυπήσει;": "injury",
        "Γιατί με παίρνεις από άλλο κινητό;": "phone_reason",
        "Πόσα θέλεις;": "amount",
        "Πες μου τι πρέπει να κάνω.": "action",
    }

    allowed = {
        "accident",
        "injury",
        "location",
        "phone_reason",
        "identity",
        "amount",
        "action",
        "urgency_reason",
        "other_person",
        "verification",
        "payment_method",
        "sensitive_credentials",
        "general",
    }

    for utterance, expected in cases.items():
        result = route_by_rules(
            utterance,
            allowed,
        )
        assert result is not None
        assert result.topic == expected
        assert result.source == "rules"
        assert result.confidence >= 0.99


def test_amount_question_is_not_treated_as_compliance():
    engine = AiScenarioEngine(
        ROOT / "data" / "ai_scenarios.json"
    )
    assert engine.classify("Πόσα θέλεις;") == "question"
    assert engine.classify(
        "Πόσο είναι το ποσό;"
    ) == "question"


def test_ollama_router_returns_enum_only(monkeypatch):
    provider = OllamaSemanticRouter(
        model="qwen3.5:4b",
        keep_alive=-1,
    )

    captured = {}

    def fake_request(path, *, payload=None, timeout=None):
        captured["payload"] = payload
        return {
            "message": {
                "content": json.dumps(
                    {
                        "topic": "verification",
                        "confidence": 0.91,
                    }
                )
            },
            "total_duration": 700_000_000,
            "load_duration": 4_000_000,
            "prompt_eval_duration": 450_000_000,
            "eval_duration": 160_000_000,
            "prompt_eval_count": 95,
            "eval_count": 12,
        }

    monkeypatch.setattr(
        provider,
        "_request",
        fake_request,
    )

    result = provider.route(
        "Κάτι δεν μου κολλάει σε αυτό που λες.",
        allowed_topics=(
            "verification",
            "general",
        ),
        stage="urgency",
        deterministic_intent="challenge",
    )

    assert result.topic == "verification"
    assert result.source == "ollama"
    assert result.confidence == 0.91

    payload = captured["payload"]
    assert payload["think"] is False
    assert payload["keep_alive"] == -1
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_ctx"] == 768
    assert payload["options"]["num_predict"] == 28

    # The model is only classifying; it has no reply field.
    properties = payload["format"]["properties"]
    assert set(properties) == {
        "topic",
        "confidence",
    }


def test_hybrid_router_fails_closed_to_topic(monkeypatch):
    provider = OllamaSemanticRouter(
        model="qwen3.5:4b"
    )

    def fail_request(*args, **kwargs):
        raise SemanticRouterError("offline")

    monkeypatch.setattr(
        provider,
        "_request",
        fail_request,
    )

    router = HybridSemanticRouter(provider)
    result = router.route(
        "Αυτό που λες δεν με πείθει.",
        allowed_topics=(
            "verification",
            "general",
        ),
        stage="establish",
        deterministic_intent="challenge",
    )

    assert result.topic == "verification"
    assert result.source == "deterministic_fallback"
    assert result.confidence == 0




def test_router_scrubber_removes_common_identifiers():
    scrubbed = _scrub_for_router(
        "test@example.com https://example.com 6912345678"
    )
    assert "test@example.com" not in scrubbed
    assert "https://example.com" not in scrubbed
    assert "6912345678" not in scrubbed


def test_independent_family_verification_is_terminal():
    engine = AiScenarioEngine(
        ROOT / "data" / "ai_scenarios.json"
    )
    assert engine.classify(
        "Θα πάρω τον πατέρα σου να το επιβεβαιώσω."
    ) == "verify"


def test_approved_response_engine_returns_only_authored_text():
    engine = AiScenarioEngine(
        ROOT / "data" / "ai_scenarios.json"
    )
    approved = ApprovedResponseEngine(engine)

    selection = approved.select(
        scenario_id="family_emergency_001",
        stage_id="establish",
        topic="phone_reason",
        deterministic_intent="question",
        visitor_text=(
            "Γιατί με παίρνεις από άλλο κινητό;"
        ),
        turn=1,
        canonical_reply=(
            "Είμαι καλά, αλλά δεν μπορώ να μιλήσω πολύ."
        ),
    )

    bank = engine.scenarios[
        "family_emergency_001"
    ]["stages"]["establish"][
        "approved_responses"
    ]["phone_reason"]

    assert selection.text in bank
    assert selection.source == "approved_bank"


def test_every_stage_has_general_and_core_topic_responses():
    engine = AiScenarioEngine(
        ROOT / "data" / "ai_scenarios.json"
    )

    required = {
        "injury",
        "location",
        "phone_reason",
        "amount",
        "action",
        "verification",
        "general",
    }

    stages = engine.scenarios[
        "family_emergency_001"
    ]["stages"]

    for stage in stages.values():
        assert required.issubset(
            stage["approved_responses"].keys()
        )
