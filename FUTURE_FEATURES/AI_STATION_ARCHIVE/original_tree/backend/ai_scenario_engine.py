# STATION4_SEMANTIC_ROUTER_V043
from __future__ import annotations

import json
import re
import secrets
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class AiScenarioError(RuntimeError):
    pass


class AiSessionNotFound(KeyError):
    pass


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class SessionState:
    scenario_id: str
    stage: str
    score: int
    turn: int
    created_at: float
    touched_at: float
    llm_history: list[dict[str, str]] = field(default_factory=list)


class AiScenarioEngine:
    """Bounded, deterministic conversation engine for Station 4 v0.1.

    This is deliberately NOT a free-form chatbot. Visitor text is classified
    into a small set of intents; the scenario graph and allowed replies come
    only from ai_scenarios.json.
    """

    STRONG_VERIFY = (
        "θα σε παρω", "θα σε καλεσω", "θα καλεσω", "θα παρω τηλεφωνο",
        "θα τηλεφωνησω", "θα μιλησω με", "αλλον συγγενη", "αλλη συγγενη",
        "θα παρω τον πατερα", "θα παρω τη μητερα", "θα παρω την μητερα",
        "θα παρω τον αδελφο", "θα παρω την αδελφη",
        "θα παρω καποιον δικο", "θα παρω καποιον αλλον",
        "θα το επιβεβαιωσω", "να το επιβεβαιωσω απο αλλου",
        "βιντεοκληση", "video call", "επισημο τηλεφωνο", "αστυνομια",
        "100", "112",
    )
    STOP = (
        "κλεινω", "τερματιζω", "δεν συνεχιζω", "σταματα", "σταματω",
        "δεν μιλαω", "δεν θα συνεχισω", "τελος",
    )
    RESIST = (
        "δεν πληρωνω", "δεν θα πληρωσω", "δεν στελνω", "δεν θα στειλω",
        "δεν δινω", "δεν θα δωσω", "δεν σου δινω", "αρνουμαι",
    )
    CHALLENGE = (
        "ποιος εισαι", "ποια εισαι", "πες μου κατι", "κωδικη λεξη",
        "μυστικη λεξη", "πως σε λενε", "που μενεις", "γενεθλια",
        "αποδειξε", "πως ξερω οτι",
    )
    COMPLY = (
        "θα πληρωσω", "θα στειλω", "θα τα στειλω", "θα τα δωσω",
        "ενταξει θα", "πες μου που", "σε ποιον λογαριασμο", "iban",
        "κανω μεταφορα", "θα κανω μεταφορα",
    )
    SENSITIVE = (
        "κωδικος", "otp", "pin", "καρτα", "cvv", "κωδικο μιας χρησης",
        "e-banking", "ebanking",
    )
    QUESTION = (
        "τι εγινε", "που εισαι", "εισαι καλα", "τι συνεβη", "γιατι",
        "ποσα", "ποσο", "πως", "που", "τι πρεπει να κανω", "τι να κανω",
        "πες μου τι", "τι θελεις να κανω", "γιατι με παιρνεις",
        "δικο σου κινητο", "αλλο κινητο", "εχεις χτυπησει", "χτυπησες",
    )

    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.payload = self._load()
        self.scenarios = {
            item["id"]: item for item in self.payload["scenarios"]
        }
        self.default_scenario_id = self.payload["default_scenario_id"]
        self._validate()

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AiScenarioError(f"Cannot load AI scenario data: {exc}") from exc

    def _validate(self) -> None:
        if self.default_scenario_id not in self.scenarios:
            raise AiScenarioError("default_scenario_id does not exist")

        for scenario_id, scenario in self.scenarios.items():
            stages = scenario.get("stages", {})
            start = scenario.get("start_stage")
            if start not in stages:
                raise AiScenarioError(f"{scenario_id}: invalid start_stage")
            if not scenario.get("opening"):
                raise AiScenarioError(f"{scenario_id}: opening is required")
            for stage_id, stage in stages.items():
                nxt = stage.get("next_stage")
                if nxt is not None and nxt not in stages:
                    raise AiScenarioError(
                        f"{scenario_id}: broken stage {stage_id} -> {nxt}"
                    )
                replies = stage.get("replies", {})
                if "default" not in replies:
                    raise AiScenarioError(
                        f"{scenario_id}:{stage_id}: default reply missing"
                    )

    def public_scenario(self, scenario_id: str | None = None) -> dict[str, Any]:
        scenario = self.scenarios[scenario_id or self.default_scenario_id]
        return {
            "id": scenario["id"],
            "station_label": scenario["station_label"],
            "intro_title": scenario["intro_title"],
            "intro_body": scenario["intro_body"],
            "opening": scenario["opening"],
            "speaker_label": scenario["speaker_label"],
            "privacy_note": scenario["privacy_note"],
        }

    def llm_profile(self, scenario_id: str, stage_id: str) -> dict[str, Any]:
        scenario = self.scenarios[scenario_id]
        stage = scenario["stages"][stage_id]
        llm = stage.get("llm", {})
        return {
            "persona": scenario.get("llm_persona", {}),
            "memory_turns": int(scenario.get("llm_memory_turns", 2)),
            "goal": llm.get("goal", ""),
            "pressure_level": int(llm.get("pressure_level", 1)),
            "style": llm.get("style", ""),
            "allowed_facts": list(llm.get("allowed_facts", [])),
        }

    def classify(self, visitor_text: str) -> str:
        text = _fold(visitor_text)
        if any(token in text for token in self.STRONG_VERIFY):
            return "verify"
        if any(token in text for token in self.STOP):
            return "stop"
        if any(token in text for token in self.RESIST):
            return "resist"
        if any(token in text for token in self.CHALLENGE):
            return "challenge"
        if any(token in text for token in self.COMPLY):
            return "comply"
        if any(token in text for token in self.SENSITIVE):
            return "sensitive"
        if "?" in visitor_text or any(token in text for token in self.QUESTION):
            return "question"
        return "default"

    @staticmethod
    def _clamp(score: int) -> int:
        return max(0, min(100, int(score)))

    def turn(self, state: SessionState, visitor_text: str) -> dict[str, Any]:
        scenario = self.scenarios[state.scenario_id]
        intent = self.classify(visitor_text)

        terminal_outcomes = scenario["terminal_outcomes"]
        if intent == "verify":
            state.score = 100
            return self._terminal_payload(state, "verified", intent, terminal_outcomes)
        if intent == "stop":
            state.score = self._clamp(max(state.score, 85))
            return self._terminal_payload(state, "stopped", intent, terminal_outcomes)

        reply_stage_id = state.stage
        stage = scenario["stages"][reply_stage_id]
        score_delta = int(stage.get("score_delta", {}).get(intent, 0))
        state.score = self._clamp(state.score + score_delta)
        state.turn += 1

        reply_key = intent if intent in stage["replies"] else "default"
        assistant_text = stage["replies"][reply_key]

        if state.turn >= int(scenario.get("max_turns", 5)):
            return self._terminal_payload(
                state,
                "pressure_completed",
                intent,
                terminal_outcomes,
                assistant_text=assistant_text,
            )

        next_stage = stage.get("next_stage")
        if next_stage is None:
            return self._terminal_payload(
                state,
                "pressure_completed",
                intent,
                terminal_outcomes,
                assistant_text=assistant_text,
            )

        state.stage = next_stage
        return {
            "terminal": False,
            "assistant_text": assistant_text,
            "intent": intent,
            "reply_stage": reply_stage_id,
            "stage": state.stage,
            "turn": state.turn,
            "score": state.score,
        }

    def _terminal_payload(
        self,
        state: SessionState,
        outcome_id: str,
        intent: str,
        outcomes: dict[str, Any],
        assistant_text: str | None = None,
    ) -> dict[str, Any]:
        outcome = outcomes[outcome_id]
        return {
            "terminal": True,
            "assistant_text": assistant_text or outcome["assistant_text"],
            "intent": intent,
            "reply_stage": state.stage,
            "stage": "result",
            "turn": state.turn,
            "score": state.score,
            "outcome": {
                "id": outcome_id,
                "title": outcome["title"],
                "summary": outcome["summary"],
                "takeaway": outcome["takeaway"],
                "red_flags": outcome["red_flags"],
            },
        }


class AiSessionStore:
    """Short-lived in-memory state.

    Raw visitor utterances are never persisted. Station 4 v0.4.1 may keep a
    tiny sanitized conversational memory inside the in-memory session only.
    It expires with the session and is never written to disk.
    """

    def __init__(self, engine: AiScenarioEngine, ttl_seconds: int = 600):
        self.engine = engine
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def _cleanup_locked(self, now: float) -> None:
        expired = [
            sid for sid, state in self._sessions.items()
            if now - state.touched_at > self.ttl_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)

    def start(self, scenario_id: str | None = None) -> tuple[str, SessionState, dict[str, Any]]:
        sid = scenario_id or self.engine.default_scenario_id
        if sid not in self.engine.scenarios:
            raise AiScenarioNotFound(sid)
        scenario = self.engine.scenarios[sid]
        now = time.monotonic()
        state = SessionState(
            scenario_id=sid,
            stage=scenario["start_stage"],
            score=int(scenario.get("initial_score", 50)),
            turn=0,
            created_at=now,
            touched_at=now,
        )
        session_id = secrets.token_urlsafe(18)
        with self._lock:
            self._cleanup_locked(now)
            self._sessions[session_id] = state
        return session_id, state, self.engine.public_scenario(sid)

    def llm_snapshot(self, session_id: str) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            state = self._sessions.get(session_id)
            if state is None:
                raise AiSessionNotFound(session_id)
            return {
                "scenario_id": state.scenario_id,
                "stage": state.stage,
                "history": [dict(item) for item in state.llm_history],
            }

    def remember_llm_exchange(
        self,
        session_id: str,
        visitor_text: str,
        assistant_text: str,
        *,
        max_turns: int = 3,
    ) -> None:
        limit = max(0, min(3, int(max_turns)))
        if limit == 0:
            return

        visitor = re.sub(r"\s+", " ", str(visitor_text or "")).strip()[:280]
        caller = re.sub(r"\s+", " ", str(assistant_text or "")).strip()[:240]
        if not visitor and not caller:
            return

        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            state = self._sessions.get(session_id)
            if state is None:
                raise AiSessionNotFound(session_id)
            state.llm_history.append({
                "visitor": visitor,
                "caller": caller,
            })
            if len(state.llm_history) > limit:
                state.llm_history[:] = state.llm_history[-limit:]

    def turn(self, session_id: str, visitor_text: str) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            state = self._sessions.get(session_id)
            if state is None:
                raise AiSessionNotFound(session_id)
            state.touched_at = now
            result = self.engine.turn(state, visitor_text)
            if result["terminal"]:
                self._sessions.pop(session_id, None)
            return result

    def end(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


class AiScenarioNotFound(KeyError):
    pass
