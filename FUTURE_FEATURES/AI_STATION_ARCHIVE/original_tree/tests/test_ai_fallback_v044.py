from __future__ import annotations

import json
from pathlib import Path

from backend.approved_response_engine import ApprovedResponseEngine
from backend.ai_scenario_engine import AiScenarioEngine

ROOT = Path(__file__).resolve().parents[1]


def _engine():
    scenario = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    responses = ApprovedResponseEngine(
        scenario,
        ROOT / "data" / "ai_fallback_corpus_v044.json",
    )
    return scenario, responses


def test_corpus_has_research_basis_and_50_plus_responses():
    payload = json.loads(
        (ROOT / "data" / "ai_fallback_corpus_v044.json").read_text(
            encoding="utf-8"
        )
    )
    count = sum(
        len(variants)
        for stage in payload["stages"].values()
        for variants in stage["responses"].values()
    )
    assert count >= 50
    assert len(payload["research_basis"]["sources"]) >= 4


def test_consistency_facts_are_locked():
    _, responses = _engine()
    facts = responses.consistency_facts()
    assert facts["relative_injured"] is False
    assert facts["own_phone_unavailable"] is True
    assert facts["exact_location"] == "unknown"
    assert facts["requested_amount_eur"] == 480
    assert facts["payment_destination"] == "never_specified"


def test_negated_injury_phrase_is_allowed_by_corpus_validator():
    scenario = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    responses = ApprovedResponseEngine(
        scenario,
        ROOT / "data" / "ai_fallback_corpus_v044.json",
    )
    assert responses.status()["version"] == "0.4.4"


def test_establish_injury_response_does_not_claim_injury():
    _, responses = _engine()
    item = responses.select(
        scenario_id="family_emergency_001",
        stage_id="establish",
        topic="injury",
        deterministic_intent="question",
        visitor_text="Έχεις χτυπήσει;",
        turn=1,
        canonical_reply="Είμαι καλά.",
    )
    folded = item.text.casefold()
    assert "τραυματίστηκα" not in folded
    assert "έχω χτυπήσει" not in folded


def test_phone_reason_is_consistent():
    _, responses = _engine()
    item = responses.select(
        scenario_id="family_emergency_001",
        stage_id="establish",
        topic="phone_reason",
        deterministic_intent="question",
        visitor_text="Γιατί με παίρνεις από άλλο κινητό;",
        turn=1,
        canonical_reply="Δεν έχω το κινητό μου.",
    )
    assert "κινητ" in item.text.casefold() or "τηλέφων" in item.text.casefold()


def test_payment_stage_performs_generic_role_handoff():
    _, responses = _engine()
    item = responses.select(
        scenario_id="family_emergency_001",
        stage_id="payment",
        topic="amount",
        deterministic_intent="question",
        visitor_text="Πόσα θέλεις;",
        turn=3,
        canonical_reply="Χρειάζονται 480 ευρώ.",
    )
    assert item.role == "case_handler"
    assert item.role_handoff is True
    assert "480 ευρώ" in item.text
    assert "χειρίζεται την υπόθεση" in item.text


def test_no_handoff_repeated_in_later_handler_stage():
    _, responses = _engine()
    item = responses.select(
        scenario_id="family_emergency_001",
        stage_id="isolation",
        topic="other_person",
        deterministic_intent="question",
        visitor_text="Θα πάρω κάποιον άλλον.",
        turn=4,
        canonical_reply="Μην πάρεις άλλον.",
    )
    assert item.role == "case_handler"
    assert item.role_handoff is False


def test_explicit_corpus_mode_uses_research_bank_with_legacy_source_contract():
    scenario = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    responses = ApprovedResponseEngine(
        scenario,
        ROOT / "data" / "ai_fallback_corpus_v044.json",
    )

    selection = responses.select(
        scenario_id="family_emergency_001",
        stage_id="establish",
        topic="phone_reason",
        deterministic_intent="question",
        visitor_text="Γιατί με παίρνεις από άλλο κινητό;",
        turn=1,
        canonical_reply="Είμαι καλά.",
    )

    assert selection.source == "approved_bank"
    assert selection.text in responses.corpus[
        "stages"
    ]["establish"]["responses"]["phone_reason"]


def test_corpus_status_reports_version_and_size():
    _, responses = _engine()
    status = responses.status()
    assert status["version"] == "0.4.4"
    assert status["responses"] == 64
    assert status["stages"] == 5


def test_v043_constructor_contract_remains_compatible():
    scenario = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    responses = ApprovedResponseEngine(scenario)
    status = responses.status()
    assert status["version"] == "0.4.3-legacy-bank"

    selection = responses.select(
        scenario_id="family_emergency_001",
        stage_id="establish",
        topic="phone_reason",
        deterministic_intent="question",
        visitor_text="Γιατί με παίρνεις από άλλο κινητό;",
        turn=1,
        canonical_reply="Είμαι καλά.",
    )

    bank = scenario.scenarios[
        "family_emergency_001"
    ]["stages"]["establish"][
        "approved_responses"
    ]["phone_reason"]

    assert selection.text in bank
    assert selection.source == "approved_bank"


def test_v044_api_keeps_approved_only_policy_and_exposes_corpus_metadata():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    started = client.post("/api/ai/session/start", json={}).json()
    response = client.post(
        f"/api/ai/session/{started['session_id']}/turn",
        json={"text": "Πού είσαι;"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["terminal"] is False
    assert body["response_policy"] == "approved_only"
    assert body["response_corpus"] == "research_fallback_corpus_v044"
    assert body["corpus_version"] == "0.4.4"
