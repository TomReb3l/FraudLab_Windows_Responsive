from __future__ import annotations

from pathlib import Path
import pytest

from backend.tts_engine import MacSayGreekTtsProvider, TtsInputError


def _exe(path: Path, source: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + source, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return path


def test_mac_say_provider_detects_greek_voice_and_returns_wav(tmp_path):
    say = _exe(tmp_path / "say", """
import pathlib, sys
if "-v" in sys.argv and "?" in sys.argv:
    print("Melina              el_GR    # Greek")
    sys.exit(0)
out = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
out.write_bytes(b"FORM" + b"0" * 256)
""")
    ffmpeg = _exe(tmp_path / "ffmpeg", """
import pathlib, sys
pathlib.Path(sys.argv[-1]).write_bytes(b"RIFF" + b"0" * 256)
""")

    provider = MacSayGreekTtsProvider(say=say, ffmpeg=ffmpeg, timeout_seconds=5)
    assert provider.status().available is True
    assert provider.status().voice == "Melina"
    assert provider.synthesize("Καλημέρα.").startswith(b"RIFF")


def test_empty_tts_text_is_rejected(tmp_path):
    say = _exe(tmp_path / "say", """
import sys
if "?" in sys.argv:
    print("Melina              el_GR    # Greek")
""")
    ffmpeg = _exe(tmp_path / "ffmpeg", "import sys\n")
    provider = MacSayGreekTtsProvider(
        say=say, ffmpeg=ffmpeg, voice="Melina", timeout_seconds=5
    )
    with pytest.raises(TtsInputError):
        provider.synthesize("   ")
