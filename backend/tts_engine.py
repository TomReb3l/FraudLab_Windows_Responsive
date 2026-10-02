# STATION4_TTS_V042_PRONUNCIATION
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_TTS_CHARS = 600
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_RATE = 175

_TTS_SPOKEN_SUBSTITUTIONS = (
    (r"\bνα\s+βγω\s+από\s+εδώ\b", "να φύγω από εδώ"),
    (r"\bβγω\b", "βγώ"),
    (r"\bβγεις\b", "βγείς"),
    (r"\bβγει\b", "βγεί"),
    (r"\bβγουν\b", "βγούν"),
)


def prepare_spoken_text(text: str) -> str:
    spoken = re.sub(r"\s+", " ", str(text or "")).strip()
    for pattern, replacement in _TTS_SPOKEN_SUBSTITUTIONS:
        spoken = re.sub(
            pattern,
            replacement,
            spoken,
            flags=re.IGNORECASE,
        )
    return spoken


class TtsError(RuntimeError):
    pass


class TtsUnavailableError(TtsError):
    pass


class TtsInputError(TtsError):
    pass


@dataclass(frozen=True)
class TtsStatus:
    provider: str
    available: bool
    voice: str | None
    detail: str
    media_type: str = "audio/wav"
    max_chars: int = MAX_TTS_CHARS

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "voice": self.voice,
            "detail": self.detail,
            "media_type": self.media_type,
            "max_chars": self.max_chars,
        }


class TtsProvider:
    def status(self) -> TtsStatus:
        raise NotImplementedError

    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError


class UnavailableTtsProvider(TtsProvider):
    def __init__(self, detail: str, provider: str = "disabled"):
        self._status = TtsStatus(
            provider=provider,
            available=False,
            voice=None,
            detail=detail,
        )

    def status(self) -> TtsStatus:
        return self._status

    def synthesize(self, text: str) -> bytes:
        raise TtsUnavailableError(self._status.detail)


class MacSayGreekTtsProvider(TtsProvider):
    # Fully local macOS TTS. Temporary AIFF/WAV files are deleted
    # automatically after each synthesis request.

    def __init__(
        self,
        *,
        say: Path,
        ffmpeg: Path,
        voice: str | None = None,
        rate: int = DEFAULT_RATE,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.say = Path(say)
        self.ffmpeg = Path(ffmpeg)
        self.explicit_voice = voice.strip() if voice else None
        self.rate = max(120, min(230, int(rate)))
        self.timeout_seconds = max(5, int(timeout_seconds))
        self._detected_voice: str | None = None

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
            raise TtsError(f"{label} timed out") from exc
        except OSError as exc:
            raise TtsError(f"{label} could not start: {exc}") from exc

    def _detect_greek_voice(self) -> str | None:
        if self.explicit_voice:
            return self.explicit_voice
        if self._detected_voice:
            return self._detected_voice

        result = self._run([str(self.say), "-v", "?"], "macOS voice discovery")
        if result.returncode != 0:
            return None

        preferred: list[str] = []
        fallback: list[str] = []

        for raw in (result.stdout or "").splitlines():
            match = re.match(r"^(\S+)\s+([a-z]{2}_[A-Z]{2})\b", raw.strip())
            if not match:
                continue
            name, locale = match.groups()
            if locale != "el_GR":
                continue
            fallback.append(name)
            if name.casefold() in {"melina", "nikos"}:
                preferred.append(name)

        chosen = preferred[0] if preferred else (fallback[0] if fallback else None)
        self._detected_voice = chosen
        return chosen

    def status(self) -> TtsStatus:
        missing: list[str] = []
        if not self.say.is_file():
            missing.append("macOS say")
        if not self.ffmpeg.is_file():
            missing.append("ffmpeg")

        voice = None
        if not missing:
            try:
                voice = self._detect_greek_voice()
            except TtsError:
                voice = None

        if voice is None:
            missing.append("installed Greek macOS voice (el_GR)")

        if missing:
            return TtsStatus(
                provider="mac_say",
                available=False,
                voice=voice,
                detail="Missing: " + ", ".join(missing),
            )

        return TtsStatus(
            provider="mac_say",
            available=True,
            voice=voice,
            detail="Local macOS Greek TTS ready",
        )

    def synthesize(self, text: str) -> bytes:
        status = self.status()
        if not status.available or not status.voice:
            raise TtsUnavailableError(status.detail)

        clean = prepare_spoken_text(text)
        if not clean:
            raise TtsInputError("Empty TTS text")
        if len(clean) > MAX_TTS_CHARS:
            raise TtsInputError("TTS text exceeds maximum length")

        with tempfile.TemporaryDirectory(prefix="fraudlab-tts-") as tmp:
            tmpdir = Path(tmp)
            aiff = tmpdir / "speech.aiff"
            wav = tmpdir / "speech.wav"

            spoken = self._run(
                [
                    str(self.say),
                    "-v",
                    status.voice,
                    "-r",
                    str(self.rate),
                    "-o",
                    str(aiff),
                    clean,
                ],
                "macOS local speech synthesis",
            )
            if spoken.returncode != 0 or not aiff.is_file() or aiff.stat().st_size < 128:
                detail = (spoken.stderr or spoken.stdout or "speech synthesis failed").strip()
                raise TtsError(detail[-600:])

            converted = self._run(
                [
                    str(self.ffmpeg),
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(aiff),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "22050",
                    "-c:a",
                    "pcm_s16le",
                    str(wav),
                ],
                "TTS WAV conversion",
            )
            if converted.returncode != 0 or not wav.is_file() or wav.stat().st_size <= 44:
                detail = (converted.stderr or converted.stdout or "audio conversion failed").strip()
                raise TtsError(detail[-600:])

            return wav.read_bytes()


def _resolve_executable(env_name: str, executable: str) -> Path | None:
    explicit = os.getenv(env_name, "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    found = shutil.which(executable)
    return Path(found).resolve() if found else None


def create_tts_provider(base_dir: Path) -> TtsProvider:
    del base_dir
    selected = os.getenv("FRAUDLAB_TTS_PROVIDER", "auto").strip().lower()

    if selected in {"off", "none", "disabled"}:
        return UnavailableTtsProvider("Local TTS disabled by FRAUDLAB_TTS_PROVIDER")

    if selected not in {"auto", "mac_say"}:
        return UnavailableTtsProvider(
            f"Unsupported local TTS provider: {selected}",
            provider=selected,
        )

    if platform.system() != "Darwin":
        return UnavailableTtsProvider(
            "Station 4 v0.3 mac_say provider requires macOS",
            provider="mac_say",
        )

    say = _resolve_executable("FRAUDLAB_SAY", "say")
    ffmpeg = _resolve_executable("FRAUDLAB_FFMPEG", "ffmpeg")
    if say is None or ffmpeg is None:
        missing = []
        if say is None:
            missing.append("say")
        if ffmpeg is None:
            missing.append("ffmpeg")
        return UnavailableTtsProvider(
            "Local Greek TTS not configured. Missing: " + ", ".join(missing),
            provider="mac_say",
        )

    voice = os.getenv("FRAUDLAB_TTS_VOICE", "").strip() or None
    rate = int(os.getenv("FRAUDLAB_TTS_RATE", str(DEFAULT_RATE)))
    timeout = int(os.getenv("FRAUDLAB_TTS_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))

    return MacSayGreekTtsProvider(
        say=say,
        ffmpeg=ffmpeg,
        voice=voice,
        rate=rate,
        timeout_seconds=timeout,
    )
