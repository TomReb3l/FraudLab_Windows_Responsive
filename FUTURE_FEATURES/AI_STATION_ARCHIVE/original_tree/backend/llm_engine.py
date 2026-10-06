# STATION4_V042_QUALITY_GATE
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_KEEP_ALIVE: int | str = -1
DEFAULT_MEMORY_TURNS = 2
MAX_MEMORY_TURNS = 3
MAX_REPLY_CHARS = 240

_GREEK_STOPWORDS = frozenset(
    {
        "αλλα", "απο", "αυτο", "για", "δεν", "ειμαι", "ειναι", "εισαι",
        "ενα", "εχει", "εχω", "και", "κατι", "λιγο", "μετα", "μην",
        "μονο", "μου", "μπορω", "να", "οτι", "πολυ", "πρεπει", "πως",
        "που", "σε", "στο", "στη", "στην", "στον", "σου", "την", "της",
        "τι", "το", "τον", "τωρα", "θα", "ακομη",
    }
)

_QUALITY_REJECT_PATTERNS = (
    r"\bθεσ\s+να\s+ακουσω\b",
    r"\bθελεισ\s+να\s+ακουσω\b",
    r"\bνα\s+ακουσω\s+για\s+λιγο\b",
    r"\bβασικ(?:η|ο)\s+απαντησ",
    r"\bstage\b",
    r"\bintent\b",
    r"\bjson\b",
)


def _fold_greek(text: str) -> str:
    folded = unicodedata.normalize("NFD", str(text or "").casefold())
    folded = "".join(
        ch for ch in folded
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", folded).strip()


def _content_anchors(text: str) -> set[str]:
    folded = _fold_greek(text)
    words = re.findall(r"[α-ω]+", folded)
    return {
        word
        for word in words
        if len(word) >= 4 and word not in _GREEK_STOPWORDS
    }


def _quality_gate(reply: str, canonical_reply: str) -> None:
    folded_reply = _fold_greek(reply)

    for pattern in _QUALITY_REJECT_PATTERNS:
        if re.search(pattern, folded_reply, flags=re.IGNORECASE):
            raise LlmOutputError(
                "Local LLM reply failed Greek quality gate"
            )

    if "?" in reply and "?" not in canonical_reply:
        raise LlmOutputError(
            "Local LLM invented a question not present in canonical reply"
        )

    canonical_anchors = _content_anchors(canonical_reply)
    reply_anchors = _content_anchors(reply)

    if len(canonical_anchors) >= 3 and not (
        canonical_anchors & reply_anchors
    ):
        raise LlmOutputError(
            "Local LLM drifted away from canonical reply meaning"
        )

    if re.search(r"\b([α-ω]{4,})\s+\1\b", folded_reply):
        raise LlmOutputError(
            "Local LLM repeated a content word"
        )


class LlmError(RuntimeError):
    pass


class LlmUnavailableError(LlmError):
    pass


class LlmOutputError(LlmError):
    pass


@dataclass(frozen=True)
class LlmStatus:
    provider: str
    available: bool
    model: str
    endpoint: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "model": self.model,
            "endpoint": self.endpoint,
            "detail": self.detail,
        }


class LlmProvider:
    def status(self) -> LlmStatus:
        raise NotImplementedError

    def reset_metrics(self) -> None:
        return None

    def last_metrics(self) -> dict[str, Any]:
        return {}

    def rewrite_reply(
        self,
        *,
        visitor_text: str,
        canonical_reply: str,
        intent: str,
        stage: str,
        history: list[dict[str, str]] | None = None,
        stage_profile: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


class UnavailableLlmProvider(LlmProvider):
    def __init__(self, detail: str, model: str = DEFAULT_MODEL):
        self._status = LlmStatus(
            provider="disabled",
            available=False,
            model=model,
            endpoint=DEFAULT_ENDPOINT,
            detail=detail,
        )

    def status(self) -> LlmStatus:
        return self._status

    def rewrite_reply(
        self,
        *,
        visitor_text: str,
        canonical_reply: str,
        intent: str,
        stage: str,
        history: list[dict[str, str]] | None = None,
        stage_profile: dict[str, Any] | None = None,
    ) -> str:
        del visitor_text, canonical_reply, intent, stage, history, stage_profile
        raise LlmUnavailableError(self._status.detail)


def scrub_visitor_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
        "[ΤΡΑΠΕΖΙΚΟ ΣΤΟΙΧΕΙΟ]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL]",
        text,
    )
    text = re.sub(
        r"https?://\S+|www\.\S+",
        "[ΣΥΝΔΕΣΜΟΣ]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:\d[\s-]?){8,}\b", "[ΑΡΙΘΜΟΣ]", text)
    return re.sub(r"\s+", " ", text).strip()[:280]


# Backward compatibility for the v0.4 tests/imports/auditor.
def _scrub_visitor_text(value: str) -> str:
    return scrub_visitor_text(value)


def _validate_reply(reply: str, canonical_reply: str) -> str:
    text = re.sub(r"\s+", " ", str(reply or "")).strip()

    if not text:
        raise LlmOutputError("Empty local LLM reply")
    if len(text) > MAX_REPLY_CHARS:
        raise LlmOutputError("Local LLM reply is too long")

    forbidden_patterns = [
        r"https?://",
        r"www\.",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
        r"\b\d{6,}\b",
        r"\b(?:otp|cvv|iban|pin)\b",
        r"αριθμ(?:ό|ος)\s+κάρτας",
        r"κωδικ(?:ό|ος)\s+μιας\s+χρήσης",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise LlmOutputError("Local LLM reply failed safety validation")

    if not re.sub(r"\s+", " ", canonical_reply).strip():
        raise LlmOutputError("Canonical reply missing")

    _quality_gate(text, canonical_reply)
    return text


def _normalize_keep_alive(value: str | int) -> str | int:
    if isinstance(value, int):
        return value
    raw = str(value).strip()
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _ns_to_ms(value: Any) -> float:
    try:
        return round(float(value) / 1_000_000.0, 1)
    except (TypeError, ValueError):
        return 0.0


class OllamaLlmProvider(LlmProvider):
    def __init__(
        self,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        keep_alive: int | str = DEFAULT_KEEP_ALIVE,
        memory_turns: int = DEFAULT_MEMORY_TURNS,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.keep_alive = _normalize_keep_alive(keep_alive)
        self.memory_turns = max(0, min(MAX_MEMORY_TURNS, int(memory_turns)))
        self._last_metrics: dict[str, Any] = {}

    def reset_metrics(self) -> None:
        self._last_metrics = {}

    def last_metrics(self) -> dict[str, Any]:
        return dict(self._last_metrics)

    def _json_request(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        url = self.endpoint + path
        data = None
        headers = {"Accept": "application/json"}

        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST" if payload is not None else "GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout or self.timeout_seconds,
            ) as response:
                body = response.read()
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            raise LlmUnavailableError(f"Local Ollama unavailable: {exc}") from exc

        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LlmOutputError("Invalid JSON from local Ollama") from exc

    def status(self) -> LlmStatus:
        try:
            payload = self._json_request("/api/tags", timeout=2)
            models = {
                item.get("name")
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }
        except LlmError as exc:
            return LlmStatus(
                provider="ollama",
                available=False,
                model=self.model,
                endpoint=self.endpoint,
                detail=str(exc),
            )

        available = self.model in models
        return LlmStatus(
            provider="ollama",
            available=available,
            model=self.model,
            endpoint=self.endpoint,
            detail="Local Ollama model ready"
            if available
            else f"Model not installed: {self.model}",
        )

    def _build_messages(
        self,
        *,
        visitor_text: str,
        canonical_reply: str,
        intent: str,
        stage: str,
        history: list[dict[str, str]] | None,
        stage_profile: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        profile = stage_profile or {}
        persona = profile.get("persona", {}) if isinstance(profile, dict) else {}
        allowed_facts = profile.get("allowed_facts", []) if isinstance(profile, dict) else []
        if not isinstance(allowed_facts, list):
            allowed_facts = []

        system = (
            "Είσαι το φανταστικό πρόσωπο μιας δημόσιας εκπαιδευτικής "
            "προσομοίωσης τηλεφωνικής εξαπάτησης. Γράφεις ΜΟΝΟ την επόμενη "
            "σύντομη ατάκα του καλούντος. Ο deterministic controller έχει ήδη "
            "αποφασίσει intent, stage, score και το βασικό νόημα. "
            "Απάντησε φυσικά στη φράση του επισκέπτη, αλλά μείνε κοντά στο "
            "εγκεκριμένο βασικό νόημα. Αν ο επισκέπτης κάνει άμεση ερώτηση, "
            "απάντησέ την πρώτα μόνο όταν τα επιτρεπόμενα γεγονότα το στηρίζουν. "
            "Μην αλλάζεις ποιος κάνει τι και μην αλλάζεις δηλωτική ατάκα σε "
            "νέα ερώτηση. Κράτησε τουλάχιστον μία σαφή έννοια ή λέξη από τη "
            "βασική απάντηση. Αν δεν είσαι βέβαιος, χρησιμοποίησε διατύπωση "
            "πολύ κοντά στη βασική απάντηση. Για καθαρή ελληνική εκφώνηση, "
            "προτίμησε «να φύγω από εδώ» αντί «να βγω από εδώ». Μπορείς να "
            "συνδέεσαι με το πρόσφατο ιστορικό, αλλά χρησιμοποίησε ΜΟΝΟ τα "
            "επιτρεπόμενα γεγονότα. Αν ζητηθεί άγνωστη λεπτομέρεια, απόφυγέ "
            "την φυσικά αντί να επινοήσεις κάτι. Μην προσθέτεις πραγματικά "
            "ονόματα, τοποθεσίες, οργανισμούς, URLs, τηλέφωνα, IBAN, PIN, OTP, "
            "CVV ή στοιχεία πληρωμής. Μην δίνεις τεχνικές παράκαμψης "
            "ασφάλειας. 1-2 σύντομες προφορικές προτάσεις, φυσικά ελληνικά, "
            "έως 240 χαρακτήρες. Επέστρεψε μόνο το JSON του schema."
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]

        memory_limit = self.memory_turns
        try:
            memory_limit = min(
                memory_limit,
                int(profile.get("memory_turns", memory_limit)),
            )
        except (TypeError, ValueError):
            pass

        for item in (history or [])[-memory_limit:]:
            visitor = scrub_visitor_text(item.get("visitor", ""))
            caller = re.sub(r"\s+", " ", str(item.get("caller", ""))).strip()[:MAX_REPLY_CHARS]
            if visitor:
                messages.append({"role": "user", "content": visitor})
            if caller:
                messages.append({"role": "assistant", "content": caller})

        facts = "\n".join(
            f"- {re.sub(r'\\s+', ' ', str(fact)).strip()}"
            for fact in allowed_facts[:6]
            if str(fact).strip()
        ) or "- Καμία πρόσθετη λεπτομέρεια."

        role = str(persona.get("role", "φανταστικός συγγενής")).strip()
        style = str(profile.get("style", persona.get("voice_style", "αγχωμένος αλλά φυσικός"))).strip()
        goal = str(profile.get("goal", "Κράτησε τη συνομιλία φυσική.")).strip()
        pressure = str(profile.get("pressure_level", 1)).strip()

        current = (
            f"ΡΟΛΟΣ: {role}\n"
            f"STAGE: {stage}\n"
            f"INTENT: {intent}\n"
            f"ΣΤΟΧΟΣ STAGE: {goal}\n"
            f"ΕΝΤΑΣΗ: {pressure}/5\n"
            f"ΥΦΟΣ: {style}\n"
            f"ΕΠΙΤΡΕΠΟΜΕΝΑ ΓΕΓΟΝΟΤΑ:\n{facts}\n"
            f"ΒΑΣΙΚΟ ΝΟΗΜΑ ΠΟΥ ΠΡΕΠΕΙ ΝΑ ΔΙΑΤΗΡΗΘΕΙ: "
            f"{re.sub(r'\\s+', ' ', canonical_reply).strip()}\n"
            f"ΤΩΡΙΝΗ ΦΡΑΣΗ ΕΠΙΣΚΕΠΤΗ: {scrub_visitor_text(visitor_text)}\n"
            "Δώσε την επόμενη φυσική ατάκα του καλούντος."
        )
        messages.append({"role": "user", "content": current})
        return messages

    def rewrite_reply(
        self,
        *,
        visitor_text: str,
        canonical_reply: str,
        intent: str,
        stage: str,
        history: list[dict[str, str]] | None = None,
        stage_profile: dict[str, Any] | None = None,
    ) -> str:
        self.reset_metrics()
        started = time.perf_counter()

        schema = {
            "type": "object",
            "properties": {
                "reply": {
                    "type": "string",
                    "maxLength": MAX_REPLY_CHARS,
                }
            },
            "required": ["reply"],
            "additionalProperties": False,
        }

        payload = {
            "model": self.model,
            "messages": self._build_messages(
                visitor_text=visitor_text,
                canonical_reply=canonical_reply,
                intent=intent,
                stage=stage,
                history=history,
                stage_profile=stage_profile,
            ),
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "format": schema,
            "options": {
                "temperature": 0.55,
                "top_p": 0.9,
                "top_k": 30,
                "num_ctx": 2048,
                "num_predict": 72,
            },
        }

        try:
            response = self._json_request("/api/chat", payload=payload)
        except LlmError:
            self._last_metrics = {
                "model": self.model,
                "wall_ms": round((time.perf_counter() - started) * 1000, 1),
                "failed": True,
            }
            raise

        wall_ms = round((time.perf_counter() - started) * 1000, 1)
        eval_duration = response.get("eval_duration", 0) or 0
        eval_count = response.get("eval_count", 0) or 0
        tokens_per_second = 0.0
        try:
            if float(eval_duration) > 0:
                tokens_per_second = round(
                    float(eval_count) / (float(eval_duration) / 1_000_000_000.0),
                    1,
                )
        except (TypeError, ValueError, ZeroDivisionError):
            tokens_per_second = 0.0

        self._last_metrics = {
            "model": self.model,
            "wall_ms": wall_ms,
            "total_ms": _ns_to_ms(response.get("total_duration")),
            "load_ms": _ns_to_ms(response.get("load_duration")),
            "prompt_eval_ms": _ns_to_ms(response.get("prompt_eval_duration")),
            "eval_ms": _ns_to_ms(eval_duration),
            "prompt_tokens": int(response.get("prompt_eval_count", 0) or 0),
            "output_tokens": int(eval_count or 0),
            "tokens_per_second": tokens_per_second,
            "history_turns": min(self.memory_turns, len(history or [])),
            "failed": False,
        }

        content = (
            response.get("message", {}).get("content", "")
            if isinstance(response.get("message"), dict)
            else ""
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmOutputError(
                "Local LLM did not return valid structured output"
            ) from exc

        try:
            validated = _validate_reply(
                parsed.get("reply", ""),
                canonical_reply,
            )
        except LlmOutputError as exc:
            self._last_metrics["quality_rejected"] = True
            self._last_metrics["quality_reason"] = str(exc)
            raise

        self._last_metrics["quality_rejected"] = False
        self._last_metrics["quality_reason"] = ""
        return validated


def create_llm_provider() -> LlmProvider:
    selected = os.getenv("FRAUDLAB_LLM_PROVIDER", "auto").strip().lower()
    model = os.getenv("FRAUDLAB_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    if selected in {"off", "none", "disabled"}:
        return UnavailableLlmProvider(
            "Local LLM disabled by FRAUDLAB_LLM_PROVIDER",
            model=model,
        )

    if selected not in {"auto", "ollama"}:
        return UnavailableLlmProvider(
            f"Unsupported local LLM provider: {selected}",
            model=model,
        )

    endpoint = (
        os.getenv("FRAUDLAB_OLLAMA_URL", DEFAULT_ENDPOINT).strip()
        or DEFAULT_ENDPOINT
    )
    timeout = int(
        os.getenv(
            "FRAUDLAB_LLM_TIMEOUT_SECONDS",
            str(DEFAULT_TIMEOUT_SECONDS),
        )
    )
    keep_alive_raw = os.getenv(
        "FRAUDLAB_LLM_KEEP_ALIVE",
        str(DEFAULT_KEEP_ALIVE),
    )
    memory_turns = int(
        os.getenv(
            "FRAUDLAB_LLM_MEMORY_TURNS",
            str(DEFAULT_MEMORY_TURNS),
        )
    )

    return OllamaLlmProvider(
        endpoint=endpoint,
        model=model,
        timeout_seconds=timeout,
        keep_alive=_normalize_keep_alive(keep_alive_raw),
        memory_turns=memory_turns,
    )
