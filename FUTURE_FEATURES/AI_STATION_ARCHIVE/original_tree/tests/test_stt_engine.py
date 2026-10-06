from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.stt_engine import (
    SttError,
    UnavailableSttProvider,
    WhisperCppSttProvider,
    create_stt_provider,
)


def _make_executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_disabled_provider_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAUDLAB_STT_PROVIDER", "disabled")
    provider = create_stt_provider(tmp_path)
    status = provider.status()
    assert status.available is False
    assert status.provider == "disabled"


def test_whisper_cpp_provider_uses_temp_files_and_returns_text(tmp_path):
    model = tmp_path / "ggml-small.bin"
    model.write_bytes(b"model")

    ffmpeg = _make_executable(
        tmp_path / "ffmpeg",
        """
import pathlib, sys
out = pathlib.Path(sys.argv[-1])
out.write_bytes(b'RIFF' + b'0' * 128)
sys.exit(0)
""",
    )

    whisper = _make_executable(
        tmp_path / "whisper-cli",
        """
import pathlib, sys
args = sys.argv
base = pathlib.Path(args[args.index('-of') + 1])
(base.parent / (base.name + '.txt')).write_text('  Θα σε καλέσω εγώ ξανά.  ', encoding='utf-8')
sys.exit(0)
""",
    )

    provider = WhisperCppSttProvider(
        whisper_cli=whisper,
        ffmpeg=ffmpeg,
        model=model,
        timeout_seconds=5,
    )
    result = provider.transcribe(
        b"fake-browser-audio",
        content_type="audio/webm;codecs=opus",
        duration_ms=1200,
    )
    assert result["text"] == "Θα σε καλέσω εγώ ξανά."
    assert result["provider"] == "whisper_cpp"
    assert result["language"] == "el"
    assert result["model"] == "ggml-small.bin"
    assert result["duration_ms"] == 1200


def test_whisper_cpp_requires_output_file_even_on_zero_exit(tmp_path):
    model = tmp_path / "ggml-small.bin"
    model.write_bytes(b"model")

    ffmpeg = _make_executable(
        tmp_path / "ffmpeg",
        """
import pathlib, sys
pathlib.Path(sys.argv[-1]).write_bytes(b'RIFF' + b'0' * 128)
sys.exit(0)
""",
    )
    whisper = _make_executable(
        tmp_path / "whisper-cli",
        "import sys\nsys.exit(0)\n",
    )

    provider = WhisperCppSttProvider(
        whisper_cli=whisper,
        ffmpeg=ffmpeg,
        model=model,
        timeout_seconds=5,
    )
    with pytest.raises(SttError):
        provider.transcribe(b"audio", content_type="audio/webm")


def test_english_only_model_is_rejected_for_greek(tmp_path):
    model = tmp_path / "ggml-small.en.bin"
    model.write_bytes(b"model")
    exe = _make_executable(tmp_path / "tool", "")
    provider = WhisperCppSttProvider(
        whisper_cli=exe,
        ffmpeg=exe,
        model=model,
    )
    assert provider.status().available is False
