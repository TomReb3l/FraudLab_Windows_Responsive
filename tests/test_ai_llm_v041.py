from __future__ import annotations

import json
from pathlib import Path

from backend.ai_scenario_engine import AiScenarioEngine, AiSessionStore
from backend.llm_engine import OllamaLlmProvider, scrub_visitor_text


ROOT = Path(__file__).resolve().parents[1]


def test_stage_profile_and_memory_contract():
    engine = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    profile = engine.llm_profile("family_emergency_001", "establish")

    assert profile["memory_turns"] == 2
    assert profile["pressure_level"] == 1
    assert profile["allowed_facts"]
    assert profile["persona"]["role"]


def test_session_memory_is_short_lived_and_bounded():
    engine = AiScenarioEngine(ROOT / "data" / "ai_scenarios.json")
    sessions = AiSessionStore(engine=engine, ttl_seconds=600)
    session_id, _, _ = sessions.start()

    for idx in range(5):
        sessions.remember_llm_exchange(
            session_id,
            f"visitor {idx}",
            f"caller {idx}",
            max_turns=3,
        )

    snapshot = sessions.llm_snapshot(session_id)
    assert len(snapshot["history"]) == 3
    assert snapshot["history"][0]["visitor"] == "visitor 2"

    assert sessions.end(session_id) is True


def test_llm_builds_compact_history_stage_context_and_metrics(monkeypatch):
    provider = OllamaLlmProvider(
        endpoint="http://127.0.0.1:11434",
        model="qwen3.5:4b",
        keep_alive=-1,
        memory_turns=2,
    )

    captured = {}

    def fake_request(path, *, payload=None, timeout=None):
        assert path == "/api/chat"
        captured["payload"] = payload
        return {
            "message": {
                "content": json.dumps(
                    {"reply": "Μη με κλείσεις τώρα, σε παρακαλώ. Άκουσέ με λίγο ακόμη."},
                    ensure_ascii=False,
                )
            },
            "total_duration": 900_000_000,
            "load_duration": 10_000_000,
            "prompt_eval_count": 180,
            "prompt_eval_duration": 200_000_000,
            "eval_count": 24,
            "eval_duration": 500_000_000,
        }

    monkeypatch.setattr(provider, "_json_request", fake_request)

    reply = provider.rewrite_reply(
        visitor_text="Γιατί δεν με παίρνεις από το δικό σου κινητό;",
        canonical_reply="Δεν μπορώ να μιλήσω πολύ. Μη με κλείσεις ακόμη.",
        intent="question",
        stage="establish",
        history=[
            {
                "visitor": "Τι έγινε;",
                "caller": "Έγινε ένα ατύχημα και χρειάζομαι βοήθεια.",
            },
            {
                "visitor": "Είσαι καλά;",
                "caller": "Είμαι καλά, αλλά είμαι πολύ πιεσμένος.",
            },
            {
                "visitor": "Πού είσαι;",
                "caller": "Δεν μπορώ να μιλήσω πολύ τώρα.",
            },
        ],
        stage_profile={
            "memory_turns": 2,
            "goal": "Κράτησε τον επισκέπτη στη γραμμή.",
            "pressure_level": 2,
            "style": "αγχωμένος αλλά φυσικός",
            "persona": {"role": "φανταστικός συγγενής"},
            "allowed_facts": [
                "Έγινε ένα ατύχημα.",
                "Δεν μπορεί να μιλήσει για πολλή ώρα.",
            ],
        },
    )

    assert reply.startswith("Μη με κλείσεις")
    payload = captured["payload"]
    assert payload["think"] is False
    assert payload["keep_alive"] == -1
    assert payload["options"]["num_ctx"] == 2048
    assert payload["options"]["num_predict"] == 72
    assert payload["options"]["temperature"] == 0.55

    contents = "\n".join(item["content"] for item in payload["messages"])
    assert "Είσαι καλά;" in contents
    assert "Πού είσαι;" in contents
    assert "Τι έγινε;" not in contents
    assert "Έγινε ένα ατύχημα." in contents
    assert "Κράτησε τον επισκέπτη στη γραμμή." in contents

    metrics = provider.last_metrics()
    assert metrics["total_ms"] == 900.0
    assert metrics["load_ms"] == 10.0
    assert metrics["prompt_tokens"] == 180
    assert metrics["output_tokens"] == 24
    assert metrics["tokens_per_second"] == 48.0
    assert metrics["history_turns"] == 2


def test_scrubbed_memory_does_not_keep_common_identifiers():
    scrubbed = scrub_visitor_text(
        "Πάρε με στο 6912345678 ή δες https://example.com"
    )
    assert "6912345678" not in scrubbed
    assert "https://example.com" not in scrubbed
