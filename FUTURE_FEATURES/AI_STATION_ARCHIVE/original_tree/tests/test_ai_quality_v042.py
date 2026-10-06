from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from backend.llm_engine import LlmOutputError, _validate_reply
from backend.tts_engine import prepare_spoken_text


ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_rejects_new_question_not_in_canonical():
    with pytest.raises(LlmOutputError):
        _validate_reply(
            "Είμαι πολύ πιεσμένος. Θες να ακούσω για λίγο;",
            "Είμαι καλά, αλλά δεν μπορώ να μιλήσω πολύ.",
        )


def test_quality_gate_rejects_semantic_drift_without_content_anchor():
    with pytest.raises(LlmOutputError):
        _validate_reply(
            "Όχι, δεν έχω χτυπηθεί, αλλά είμαι πολύ πιεσμένος με το άγχος.",
            (
                "Είμαι καλά, αλλά δεν μπορώ να μιλήσω πολύ. "
                "Έγινε ένα ατύχημα και πρέπει να τακτοποιηθεί κάτι άμεσα."
            ),
        )


def test_quality_gate_accepts_natural_reply_that_keeps_anchor():
    text = _validate_reply(
        (
            "Είμαι καλά, αλλά έγινε ένα ατύχημα και δεν μπορώ "
            "να μιλήσω για πολλή ώρα."
        ),
        (
            "Είμαι καλά, αλλά δεν μπορώ να μιλήσω πολύ. "
            "Έγινε ένα ατύχημα."
        ),
    )
    assert "ατύχημα" in text


def test_tts_pronunciation_normalizes_problem_phrase_only_for_speech():
    displayed = "Χρειάζομαι να βγω από εδώ."
    spoken = prepare_spoken_text(displayed)
    assert displayed == "Χρειάζομαι να βγω από εδώ."
    assert "να φύγω από εδώ" in spoken


def test_benchmark_is_directly_invokable_from_repo_root():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "benchmark_station4_llm.py"),
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--models" in result.stdout
