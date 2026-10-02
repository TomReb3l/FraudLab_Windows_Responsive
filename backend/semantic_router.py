from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_TIMEOUT_SECONDS = 1.0
DEFAULT_KEEP_ALIVE: int | str = -1
DEFAULT_MIN_CONFIDENCE = 0.62

CRITICAL_TOPICS = frozenset([
    "injury", "location", "identity", "phone_reason", "verification", "sensitive_credentials"
])

TOPICS = (
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
)


class SemanticRouterError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticRoute:
    topic: str
    confidence: float
    source: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "confidence": round(float(self.confidence), 3),
            "source": self.source,
        }


@dataclass(frozen=True)
class SemanticRouterStatus:
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


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text or "").casefold())
    value = "".join(
        ch for ch in value
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", value).strip()


def _scrub_for_router(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
        "[ΤΡΑΠΕΖΙΚΟ ΣΤΟΙΧΕΙΟ]",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL]",
        value,
    )
    value = re.sub(
        r"https?://\S+|www\.\S+",
        "[ΣΥΝΔΕΣΜΟΣ]",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(?:\d[\s-]?){8,}\b",
        "[ΑΡΙΘΜΟΣ]",
        value,
    )
    return re.sub(r"\s+", " ", value).strip()[:280]


_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "sensitive_credentials",
        (
            r"\botp\b",
            r"\bpin\b",
            r"\bcvv\b",
            r"\bκωδικ",
            r"\bκαρτ",
            r"\bebanking\b",
            r"\be-banking\b",
        ),
    ),
    (
        "phone_reason",
        (
            r"δικο σου κινητο",
            r"δικο σου τηλεφωνο",
            r"αλλο κινητο",
            r"αλλο τηλεφωνο",
            r"αγνωστο αριθ",
            r"γιατι με παιρν",
            r"γιατι τηλεφων",
            r"απο ποιο τηλεφων",
        ),
    ),
    (
        "injury",
        (
            r"εχεις χτυπη",
            r"χτυπησ",
            r"τραυματ",
            r"εισαι καλα",
            r"επαθες κατι",
        ),
    ),
    (
        "location",
        (
            r"\bπου εισαι\b",
            r"\bπου βρισκεσαι\b",
            r"\bπου βρισκεστε\b",
            r"σε ποιο μερος",
            r"σε ποιο σημειο",
        ),
    ),
    (
        "identity",
        (
            r"ποιος εισαι",
            r"ποια εισαι",
            r"εισαι εσυ",
            r"πως σε λενε",
            r"πες μου ποιος",
            r"πες μου ποια",
        ),
    ),
    (
        "amount",
        (
            r"\bποσα\b",
            r"\bποσο\b",
            r"\bευρω\b",
            r"\bχρηματα\b",
            r"\bλεφτα\b",
            r"τι ποσο",
        ),
    ),
    (
        "payment_method",
        (
            r"πως να πληρω",
            r"πως θα πληρω",
            r"πως να στειλω",
            r"πως θα στειλω",
            r"πως θα γινει η μεταφορ",
            r"τραπεζικη εφαρμογ",
            r"τραπεζα",
            r"μεταφορα",
            r"λογαριασμ",
        ),
    ),
    (
        "action",
        (
            r"τι πρεπει να κανω",
            r"τι να κανω",
            r"πες μου τι πρεπει",
            r"πες μου τι να",
            r"τι θελεις να κανω",
            r"πως να σε βοηθησω",
            r"τι χρειαζεται να κανω",
        ),
    ),
    (
        "verification",
        (
            r"πως ξερω οτι εισαι",
            r"πως να ξερω οτι εισαι",
            r"πως θα σε επιβεβαι",
            r"να το επιβεβαιω",
            r"αποδειξε οτι εισαι",
            r"δεν σε πιστευ",
            r"δεν μου κολλα",
            r"δεν μου ακουγεται σωστ",
            r"μου φαινεται περιεργ",
        ),
    ),
    (
        "other_person",
        (
            r"καποιον αλλον",
            r"καποια αλλη",
            r"τον πατερα",
            r"τη μητερα",
            r"την μητερα",
            r"τον αδελφο",
            r"την αδελφη",
            r"συγγεν",
        ),
    ),
    (
        "urgency_reason",
        (
            r"γιατι βιαζ",
            r"γιατι τωρα",
            r"γιατι τοσο γρηγορα",
            r"γιατι επειγει",
            r"τι βιασυνη",
            r"γιατι δεν περιμεν",
        ),
    ),
    (
        "accident",
        (
            r"τι εγινε",
            r"τι συνεβη",
            r"τι ατυχημα",
            r"\bατυχημα\b",
            r"τι επαθες",
        ),
    ),
)


def route_by_rules(
    visitor_text: str,
    allowed_topics: Iterable[str],
) -> SemanticRoute | None:
    allowed = set(allowed_topics)
    folded = _fold(visitor_text)

    for topic, patterns in _RULES:
        if (
            topic not in allowed
            and topic not in CRITICAL_TOPICS
        ):
            continue
        if any(re.search(pattern, folded) for pattern in patterns):
            return SemanticRoute(
                topic=topic,
                confidence=0.99,
                source="rules",
                metrics={
                    "wall_ms": 0.0,
                    "model_ms": 0.0,
                    "prompt_ms": 0.0,
                    "eval_ms": 0.0,
                    "output_tokens": 0,
                },
            )

    return None


def _fallback_topic(
    deterministic_intent: str,
    allowed_topics: Iterable[str],
) -> str:
    allowed = set(allowed_topics)

    preferred = {
        "sensitive": "sensitive_credentials",
        "challenge": "verification",
        "comply": "action",
        "resist": "general",
        "question": "general",
        "default": "general",
    }.get(deterministic_intent, "general")

    if preferred in allowed:
        return preferred
    if "general" in allowed:
        return "general"
    return next(iter(allowed), "general")


class OllamaSemanticRouter:
    def __init__(
        self,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        keep_alive: int | str = DEFAULT_KEEP_ALIVE,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.keep_alive = keep_alive
        self.min_confidence = max(0.0, min(1.0, float(min_confidence)))

    def _request(
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
            data = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")
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
                raw = response.read()
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            raise SemanticRouterError(
                f"Local semantic router unavailable: {exc}"
            ) from exc

        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SemanticRouterError(
                "Invalid JSON from local semantic router"
            ) from exc

    def status(self) -> SemanticRouterStatus:
        try:
            payload = self._request("/api/tags", timeout=2)
            names = {
                item.get("name")
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }
        except SemanticRouterError as exc:
            return SemanticRouterStatus(
                provider="ollama_semantic_router",
                available=False,
                model=self.model,
                endpoint=self.endpoint,
                detail=str(exc),
            )

        available = self.model in names
        return SemanticRouterStatus(
            provider="ollama_semantic_router",
            available=available,
            model=self.model,
            endpoint=self.endpoint,
            detail=(
                "Local semantic router ready"
                if available
                else f"Model not installed: {self.model}"
            ),
        )

    @staticmethod
    def _ns(value: Any) -> float:
        try:
            return round(float(value or 0) / 1_000_000.0, 3)
        except (TypeError, ValueError):
            return 0.0

    def route(
        self,
        visitor_text: str,
        *,
        allowed_topics: Iterable[str],
        stage: str,
        deterministic_intent: str,
    ) -> SemanticRoute:
        allowed = [
            topic
            for topic in allowed_topics
            if topic in TOPICS
        ]
        if not allowed:
            allowed = ["general"]

        schema = {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": allowed,
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
            },
            "required": ["topic", "confidence"],
            "additionalProperties": False,
        }

        topic_descriptions = {
            "accident": "ρωτά τι συνέβη ή για το ατύχημα",
            "injury": "ρωτά αν ο καλών τραυματίστηκε ή είναι καλά",
            "location": "ρωτά πού βρίσκεται ο καλών",
            "phone_reason": "ρωτά γιατί καλεί από άγνωστο/άλλο τηλέφωνο",
            "identity": "ρωτά ποιος είναι ή αν είναι πράγματι το γνωστό πρόσωπο",
            "amount": "ρωτά για ποσό ή χρήματα",
            "action": "ρωτά τι πρέπει να κάνει ή πώς να βοηθήσει",
            "urgency_reason": "ρωτά γιατί υπάρχει βιασύνη ή επείγον",
            "other_person": "αναφέρει επικοινωνία με άλλο συγγενή/τρίτο",
            "verification": "αμφισβητεί ή ζητά απόδειξη/επαλήθευση",
            "payment_method": "ρωτά πώς θα γίνει πληρωμή/μεταφορά",
            "sensitive_credentials": "αναφέρει PIN/OTP/κωδικούς/κάρτα",
            "general": "τίποτα από τα παραπάνω",
        }

        compact_topics = "; ".join(
            f"{topic}={topic_descriptions[topic]}"
            for topic in allowed
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Κατάταξε ΜΟΝΟ το νόημα της φράσης του επισκέπτη. "
                        "Δεν γράφεις απάντηση και δεν συνεχίζεις το σενάριο. "
                        "Διάλεξε ακριβώς ένα topic από το schema."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"stage={stage}; intent={deterministic_intent}\n"
                        f"topics: {compact_topics}\n"
                        f"φράση: {_scrub_for_router(visitor_text)}"
                    ),
                },
            ],
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "format": schema,
            "options": {
                "temperature": 0,
                "top_p": 0.1,
                "num_predict": 28,
                "num_ctx": 768,
            },
        }

        started = time.perf_counter()
        response = self._request(
            "/api/chat",
            payload=payload,
        )
        wall_ms = round(
            (time.perf_counter() - started) * 1000.0,
            3,
        )

        content = (
            response.get("message", {}).get("content", "")
            if isinstance(response.get("message"), dict)
            else ""
        )

        try:
            parsed = json.loads(content)
            topic = str(parsed["topic"])
            confidence = float(parsed["confidence"])
        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise SemanticRouterError(
                "Semantic router returned invalid structured output"
            ) from exc

        if topic not in allowed:
            raise SemanticRouterError(
                "Semantic router returned a disallowed topic"
            )

        metrics = {
            "wall_ms": wall_ms,
            "model_ms": self._ns(response.get("total_duration")),
            "load_ms": self._ns(response.get("load_duration")),
            "prompt_ms": self._ns(
                response.get("prompt_eval_duration")
            ),
            "eval_ms": self._ns(response.get("eval_duration")),
            "prompt_tokens": int(
                response.get("prompt_eval_count") or 0
            ),
            "output_tokens": int(
                response.get("eval_count") or 0
            ),
        }

        return SemanticRoute(
            topic=topic,
            confidence=max(0.0, min(1.0, confidence)),
            source="ollama",
            metrics=metrics,
        )


class HybridSemanticRouter:
    """Rules first, local LLM only for ambiguous utterances.

    The router never creates visitor-facing text. It returns only an approved
    topic enum. This keeps common exhibition turns near-instant while retaining
    semantic coverage for less predictable phrasing.
    """

    def __init__(
        self,
        llm_router: OllamaSemanticRouter,
    ):
        self.llm_router = llm_router

    def status(self) -> SemanticRouterStatus:
        return self.llm_router.status()

    def route(
        self,
        visitor_text: str,
        *,
        allowed_topics: Iterable[str],
        stage: str,
        deterministic_intent: str,
    ) -> SemanticRoute:
        allowed = tuple(allowed_topics)

        rule = route_by_rules(visitor_text, allowed)
        if rule is not None:
            return rule

        try:
            candidate = self.llm_router.route(
                visitor_text,
                allowed_topics=allowed,
                stage=stage,
                deterministic_intent=deterministic_intent,
            )
            if candidate.confidence >= self.llm_router.min_confidence:
                return candidate

            return SemanticRoute(
                topic=_fallback_topic(
                    deterministic_intent,
                    allowed,
                ),
                confidence=candidate.confidence,
                source="low_confidence_fallback",
                metrics=candidate.metrics,
            )
        except SemanticRouterError:
            return SemanticRoute(
                topic=_fallback_topic(
                    deterministic_intent,
                    allowed,
                ),
                confidence=0.0,
                source="deterministic_fallback",
                metrics={
                    "wall_ms": 0.0,
                    "model_ms": 0.0,
                    "prompt_ms": 0.0,
                    "eval_ms": 0.0,
                    "output_tokens": 0,
                },
            )


def create_semantic_router() -> HybridSemanticRouter:
    model = (
        os.getenv(
            "FRAUDLAB_ROUTER_MODEL",
            os.getenv("FRAUDLAB_LLM_MODEL", DEFAULT_MODEL),
        ).strip()
        or DEFAULT_MODEL
    )
    endpoint = (
        os.getenv(
            "FRAUDLAB_OLLAMA_URL",
            DEFAULT_ENDPOINT,
        ).strip()
        or DEFAULT_ENDPOINT
    )
    timeout = float(
        os.getenv(
            "FRAUDLAB_ROUTER_TIMEOUT_SECONDS",
            str(DEFAULT_TIMEOUT_SECONDS),
        )
    )
    threshold = float(
        os.getenv(
            "FRAUDLAB_ROUTER_MIN_CONFIDENCE",
            str(DEFAULT_MIN_CONFIDENCE),
        )
    )

    return HybridSemanticRouter(
        OllamaSemanticRouter(
            endpoint=endpoint,
            model=model,
            timeout_seconds=timeout,
            keep_alive=-1,
            min_confidence=threshold,
        )
    )
