from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_AUDIO_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_LANGUAGE = "el"


class SttError(RuntimeError):
    pass


class SttUnavailableError(SttError):
    pass


class SttAudioError(SttError):
    pass


@dataclass(frozen=True)
class SttStatus:
    provider: str
    available: bool
    language: str
    model: str | None
    detail: str
    max_audio_bytes: int = MAX_AUDIO_BYTES
    max_recording_ms: int = 15000

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "language": self.language,
            "model": self.model,
            "detail": self.detail,
            "max_audio_bytes": self.max_audio_bytes,
            "max_recording_ms": self.max_recording_ms,
        }


class SttProvider:
    def status(self) -> SttStatus:
        raise NotImplementedError

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        content_type: str,
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnavailableSttProvider(SttProvider):
    def __init__(self, detail: str, provider: str = "disabled"):
        self._status = SttStatus(
            provider=provider,
            available=False,
            language=DEFAULT_LANGUAGE,
            model=None,
            detail=detail,
        )

    def status(self) -> SttStatus:
        return self._status

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        content_type: str,
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        raise SttUnavailableError(self._status.detail)


class WhisperCppSttProvider(SttProvider):
    """Local Greek STT provider backed by whisper.cpp CLI.

    Browser audio is converted to 16 kHz mono 16-bit WAV in a temporary
    directory, transcribed locally, then the temporary directory is removed.
    No recording is retained by this provider.
    """

    def __init__(
        self,
        *,
        whisper_cli: Path,
        ffmpeg: Path,
        model: Path,
        language: str = DEFAULT_LANGUAGE,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.whisper_cli = Path(whisper_cli)
        self.ffmpeg = Path(ffmpeg)
        self.model = Path(model)
        self.language = language
        self.timeout_seconds = max(5, int(timeout_seconds))

    def status(self) -> SttStatus:
        missing: list[str] = []
        if not self.whisper_cli.is_file():
            missing.append("whisper-cli")
        if not self.ffmpeg.is_file():
            missing.append("ffmpeg")
        if not self.model.is_file():
            missing.append("multilingual Whisper model")
        if self.model.name.endswith(".en.bin"):
            missing.append("Greek-capable multilingual model")

        if missing:
            return SttStatus(
                provider="whisper_cpp",
                available=False,
                language=self.language,
                model=self.model.name if self.model else None,
                detail="Missing: " + ", ".join(missing),
            )

        return SttStatus(
            provider="whisper_cpp",
            available=True,
            language=self.language,
            model=self.model.name,
            detail="Local whisper.cpp STT ready",
        )

    @staticmethod
    def _suffix_for(content_type: str) -> str:
        mime = (content_type or "").split(";", 1)[0].strip().lower()
        return {
            "audio/webm": ".webm",
            "audio/mp4": ".m4a",
            "audio/mpeg": ".mp3",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
        }.get(mime, ".audio")

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace("\ufeff", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _run(self, command: list[str], label: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SttError(f"{label} timed out") from exc
        except OSError as exc:
            raise SttError(f"{label} could not start: {exc}") from exc

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        content_type: str,
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        status = self.status()
        if not status.available:
            raise SttUnavailableError(status.detail)
        if not audio_bytes:
            raise SttAudioError("Empty audio payload")
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise SttAudioError("Audio payload exceeds local STT size limit")

        suffix = self._suffix_for(content_type)

        with tempfile.TemporaryDirectory(prefix="fraudlab-stt-") as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / f"input{suffix}"
            wav = tmpdir / "input-16k.wav"
            output_base = tmpdir / "transcript"
            output_txt = tmpdir / "transcript.txt"
            source.write_bytes(audio_bytes)

            converted = self._run(
                [
                    str(self.ffmpeg),
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(wav),
                ],
                "ffmpeg audio conversion",
            )
            if converted.returncode != 0 or not wav.is_file() or wav.stat().st_size <= 44:
                detail = (converted.stderr or converted.stdout or "audio conversion failed").strip()
                raise SttAudioError(detail[-600:])

            transcribed = self._run(
                [
                    str(self.whisper_cli),
                    "-m",
                    str(self.model),
                    "-f",
                    str(wav),
                    "-l",
                    self.language,
                    "-nt",
                    "-otxt",
                    "-of",
                    str(output_base),
                    "-np",
                ],
                "whisper.cpp transcription",
            )

            # whisper.cpp 1.9.x has had cases where decoding failure still
            # returns exit code 0. Treat the output file as the success signal.
            if transcribed.returncode != 0 or not output_txt.is_file():
                detail = (transcribed.stderr or transcribed.stdout or "transcription failed").strip()
                raise SttError(detail[-600:] or "whisper.cpp produced no transcript file")

            text = self._clean_text(output_txt.read_text(encoding="utf-8", errors="replace"))
            if not text:
                raise SttAudioError("No speech was recognized")

            truncated = len(text) > 280
            text = text[:280].rstrip()
            return {
                "text": text,
                "provider": "whisper_cpp",
                "language": self.language,
                "model": self.model.name,
                "duration_ms": duration_ms,
                "truncated": truncated,
            }


def _resolve_executable(env_name: str, executable: str) -> Path | None:
    explicit = os.getenv(env_name, "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    found = shutil.which(executable)
    return Path(found).resolve() if found else None


def _resolve_model(base_dir: Path) -> Path:
    explicit = os.getenv("FRAUDLAB_WHISPER_MODEL", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (base_dir / "models" / "whisper" / "ggml-small.bin").resolve()


def create_stt_provider(base_dir: Path) -> SttProvider:
    selected = os.getenv("FRAUDLAB_STT_PROVIDER", "auto").strip().lower()
    if selected in {"off", "none", "disabled"}:
        return UnavailableSttProvider("Local STT disabled by FRAUDLAB_STT_PROVIDER")
    if selected not in {"auto", "whisper_cpp"}:
        return UnavailableSttProvider(
            f"Unsupported local STT provider: {selected}",
            provider=selected,
        )

    cli = _resolve_executable("FRAUDLAB_WHISPER_CLI", "whisper-cli")
    ffmpeg = _resolve_executable("FRAUDLAB_FFMPEG", "ffmpeg")
    model = _resolve_model(base_dir)

    missing: list[str] = []
    if cli is None or not cli.is_file():
        missing.append("whisper-cli")
    if ffmpeg is None or not ffmpeg.is_file():
        missing.append("ffmpeg")
    if not model.is_file():
        missing.append(str(model.relative_to(base_dir)) if model.is_relative_to(base_dir) else model.name)
    if model.name.endswith(".en.bin"):
        missing.append("multilingual model required for Greek")

    if missing:
        return UnavailableSttProvider(
            "Local Greek STT not configured. Missing: " + ", ".join(missing),
            provider="whisper_cpp",
        )

    timeout = int(os.getenv("FRAUDLAB_STT_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    return WhisperCppSttProvider(
        whisper_cli=cli,
        ffmpeg=ffmpeg,
        model=model,
        language=DEFAULT_LANGUAGE,
        timeout_seconds=timeout,
    )
