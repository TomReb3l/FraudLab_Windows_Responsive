import pytest

from backend.llm_engine import (
    LlmOutputError,
    _scrub_visitor_text,
    _validate_reply,
)


def test_scrubber_removes_common_identifiers():
    text = _scrub_visitor_text(
        "email test@example.com, https://example.com και 6912345678"
    )
    assert "test@example.com" not in text
    assert "https://" not in text
    assert "6912345678" not in text


def test_validator_accepts_short_natural_reply():
    reply = _validate_reply(
        "Σε παρακαλώ, άκουσέ με λίγο. Δεν έχω πολύ χρόνο.",
        "Σε παρακαλώ, άκουσέ με για λίγο.",
    )
    assert "Σε παρακαλώ" in reply


def test_validator_rejects_operational_identifiers():
    with pytest.raises(LlmOutputError):
        _validate_reply(
            "Στείλε τα χρήματα στο IBAN GR1601101250000000012300695.",
            "Χρειάζεται να γίνει γρήγορα.",
        )
