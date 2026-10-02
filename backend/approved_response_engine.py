from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ApprovedResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApprovedResponse:
    text: str
    topic: str
    source: str
    variant: int
    response_id: str
    role: str
    speaker_label: str
    role_handoff: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "source": self.source,
            "variant": self.variant,
            "response_id": self.response_id,
            "role": self.role,
            "speaker_label": self.speaker_label,
            "role_handoff": self.role_handoff,
        }


class ApprovedResponseEngine:
    """Research-derived, approved-only response selector.

    Visitor-facing text comes only from the authored v0.4.4 corpus or, if the
    corpus is unavailable, from the deterministic canonical scenario reply.
    No generative model output reaches the visitor through this component.
    """

    _FORBIDDEN = (
        r"https?://",
        r"www\.",
        r"\b(?:iban|otp|cvv|pin)\b",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
        r"\b(?:\d[\s-]?){9,}\b",
        r"αριθμ(?:ό|ος)\s+κάρτας",
        r"κωδικ(?:ό|ος)\s+μιας\s+χρήσης",
    )

    def __init__(
        self,
        scenario_engine: Any,
        corpus_file: Path | None = None,
    ):
        self.scenario_engine = scenario_engine
        self.scenarios = scenario_engine.scenarios
        self.legacy_mode = corpus_file is None

        if self.legacy_mode:
            self.corpus_file = None
            self.corpus = None
            self._validate_legacy_bank()
        else:
            self.corpus_file = Path(corpus_file)
            self.corpus = self._load()
            self._validate()

    def _validate_legacy_bank(self) -> None:
        for scenario_id, scenario in self.scenarios.items():
            stages = scenario.get("stages", {})
            if not stages:
                raise ApprovedResponseError(
                    f"{scenario_id}: no stages"
                )

            for stage_id, stage in stages.items():
                bank = stage.get("approved_responses", {})
                if not isinstance(bank, dict) or not bank:
                    raise ApprovedResponseError(
                        f"{scenario_id}:{stage_id}: "
                        "approved_responses missing"
                    )

                for topic, variants in bank.items():
                    if not isinstance(variants, list) or not variants:
                        raise ApprovedResponseError(
                            f"{scenario_id}:{stage_id}:{topic}: "
                            "response variants missing"
                        )
                    for text in variants:
                        if not isinstance(text, str) or not text.strip():
                            raise ApprovedResponseError(
                                f"{scenario_id}:{stage_id}:{topic}: "
                                "empty approved response"
                            )
                        if len(text.strip()) > 320:
                            raise ApprovedResponseError(
                                f"{scenario_id}:{stage_id}:{topic}: "
                                "approved response too long"
                            )

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(
                self.corpus_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ApprovedResponseError(
                f"Cannot load fallback corpus: {exc}"
            ) from exc

    def _validate_response_text(
        self,
        *,
        stage_id: str,
        topic: str,
        text: str,
    ) -> None:
        clean = str(text or "").strip()
        if not clean:
            raise ApprovedResponseError(
                f"{stage_id}:{topic}: empty approved response"
            )
        if len(clean) > 360:
            raise ApprovedResponseError(
                f"{stage_id}:{topic}: approved response too long"
            )

        for pattern in self._FORBIDDEN:
            if re.search(pattern, clean, flags=re.IGNORECASE):
                raise ApprovedResponseError(
                    f"{stage_id}:{topic}: forbidden operational detail"
                )

        amount = int(
            self.corpus["consistency_facts"]["requested_amount_eur"]
        )
        found_amounts = [
            int(value)
            for value in re.findall(
                r"\b(\d{2,5})\s*(?:€|ευρώ)",
                clean,
                flags=re.IGNORECASE,
            )
        ]
        if any(value != amount for value in found_amounts):
            raise ApprovedResponseError(
                f"{stage_id}:{topic}: inconsistent amount"
            )

        if topic == "amount" and str(amount) not in clean:
            raise ApprovedResponseError(
                f"{stage_id}:{topic}: amount response must contain {amount}"
            )

        if topic == "injury":
            # relative_injured=false means positive injury claims are forbidden,
            # but explicitly negated phrases such as
            # "δεν έχω χτυπήσει σοβαρά" are valid and should pass.
            folded = clean.casefold()

            negated_safe = (
                "δεν έχω χτυπήσει",
                "δεν τραυματίστηκα",
                "δεν έχω τραυματιστεί",
                "δεν έσπασα",
            )

            positive_claims = (
                "έχω χτυπήσει",
                "τραυματίστηκα",
                "έχω τραυματιστεί",
                "έσπασα",
            )

            check_text = folded
            for safe_phrase in negated_safe:
                check_text = check_text.replace(safe_phrase, "")

            if any(token in check_text for token in positive_claims):
                raise ApprovedResponseError(
                    f"{stage_id}:{topic}: contradicts relative_injured=false"
                )

        if topic == "phone_reason":
            folded = clean.casefold()
            if "κινητ" not in folded and "τηλέφων" not in folded:
                raise ApprovedResponseError(
                    f"{stage_id}:{topic}: phone reason is not explicit"
                )

    def _validate(self) -> None:
        scenario_id = str(self.corpus.get("scenario_id", ""))
        if scenario_id not in self.scenarios:
            raise ApprovedResponseError(
                "corpus scenario_id does not exist"
            )

        if self.corpus.get("version") != "0.4.4":
            raise ApprovedResponseError(
                "unexpected fallback corpus version"
            )

        facts = self.corpus.get("consistency_facts", {})
        required_facts = {
            "accident_claimed",
            "relative_injured",
            "own_phone_unavailable",
            "exact_location",
            "requested_amount_eur",
            "authority_role",
        }
        if not required_facts.issubset(facts):
            raise ApprovedResponseError(
                "fallback corpus consistency facts incomplete"
            )

        stages = self.corpus.get("stages", {})
        scenario_stages = self.scenarios[scenario_id]["stages"]

        if set(stages) != set(scenario_stages):
            raise ApprovedResponseError(
                "fallback corpus stages do not match scenario stages"
            )

        response_count = 0

        for stage_id, stage_data in stages.items():
            role = str(stage_data.get("role", "")).strip()
            speaker_label = str(
                stage_data.get("speaker_label", "")
            ).strip()
            bank = stage_data.get("responses", {})

            if not role or not speaker_label:
                raise ApprovedResponseError(
                    f"{stage_id}: role metadata missing"
                )
            if not isinstance(bank, dict) or "general" not in bank:
                raise ApprovedResponseError(
                    f"{stage_id}: general response bank missing"
                )

            for topic, variants in bank.items():
                if not isinstance(variants, list) or not variants:
                    raise ApprovedResponseError(
                        f"{stage_id}:{topic}: variants missing"
                    )

                for text in variants:
                    response_count += 1
                    self._validate_response_text(
                        stage_id=stage_id,
                        topic=topic,
                        text=text,
                    )

        if response_count < 50:
            raise ApprovedResponseError(
                "fallback corpus is too small for exhibition use"
            )

    def status(self) -> dict[str, Any]:
        if self.legacy_mode:
            count = sum(
                len(variants)
                for scenario in self.scenarios.values()
                for stage in scenario.get("stages", {}).values()
                for variants in stage.get(
                    "approved_responses",
                    {},
                ).values()
            )
            return {
                "version": "0.4.3-legacy-bank",
                "scenario_id": "legacy",
                "responses": count,
                "stages": sum(
                    len(
                        scenario.get("stages", {})
                    )
                    for scenario in self.scenarios.values()
                ),
                "sources": 0,
                "consistency_facts": {},
            }

        count = sum(
            len(variants)
            for stage_data in self.corpus["stages"].values()
            for variants in stage_data["responses"].values()
        )
        return {
            "version": self.corpus["version"],
            "scenario_id": self.corpus["scenario_id"],
            "responses": count,
            "stages": len(self.corpus["stages"]),
            "sources": len(
                self.corpus.get(
                    "research_basis",
                    {},
                ).get("sources", [])
            ),
            "consistency_facts": dict(
                self.corpus.get("consistency_facts", {})
            ),
        }

    def consistency_facts(self) -> dict[str, Any]:
        if self.legacy_mode:
            return {}
        return dict(
            self.corpus.get("consistency_facts", {})
        )

    def stage_metadata(
        self,
        stage_id: str,
    ) -> dict[str, Any]:
        if self.legacy_mode:
            return {
                "role": "relative",
                "speaker_label": "ΑΓΝΩΣΤΟΣ ΑΡΙΘΜΟΣ",
                "handoff_intro": "",
            }

        stage = self.corpus["stages"][stage_id]
        return {
            "role": stage["role"],
            "speaker_label": stage["speaker_label"],
            "handoff_intro": stage.get("handoff_intro", ""),
        }

    def allowed_topics(
        self,
        scenario_id: str,
        stage_id: str,
    ) -> tuple[str, ...]:
        if self.legacy_mode:
            stage = self.scenarios[scenario_id]["stages"][stage_id]
            bank = stage.get("approved_responses", {})
            return tuple(bank.keys())

        if scenario_id != self.corpus["scenario_id"]:
            return ("general",)
        bank = self.corpus["stages"][stage_id]["responses"]
        return tuple(bank.keys())

    @staticmethod
    def _variant_index(
        variants: list[str],
        *,
        stage_id: str,
        topic: str,
        visitor_text: str,
        turn: int,
    ) -> int:
        if len(variants) == 1:
            return 0

        seed = (
            f"{stage_id}|{topic}|{int(turn)}|"
            f"{str(visitor_text or '').casefold().strip()}"
        ).encode("utf-8")
        digest = hashlib.sha256(seed).digest()
        return int.from_bytes(digest[:4], "big") % len(variants)

    def _is_role_handoff(self, stage_id: str) -> bool:
        if self.legacy_mode:
            return False

        stage_ids = list(self.corpus["stages"])
        index = stage_ids.index(stage_id)
        if index == 0:
            return False

        previous = self.corpus["stages"][stage_ids[index - 1]]
        current = self.corpus["stages"][stage_id]
        return previous["role"] != current["role"]

    def select(
        self,
        *,
        scenario_id: str,
        stage_id: str,
        topic: str,
        deterministic_intent: str,
        visitor_text: str,
        turn: int,
        canonical_reply: str,
    ) -> ApprovedResponse:
        if self.legacy_mode:
            scenario = self.scenarios[scenario_id]
            stage = scenario["stages"][stage_id]
            bank = stage.get("approved_responses", {})

            selected_topic = (
                topic if topic in bank else "general"
            )
            variants = bank.get(selected_topic)

            if not variants:
                text = str(canonical_reply or "").strip()
                if not text:
                    text = str(
                        stage.get("replies", {}).get(
                            deterministic_intent,
                            stage.get(
                                "replies",
                                {},
                            ).get("default", ""),
                        )
                    ).strip()
                if not text:
                    raise ApprovedResponseError(
                        "No approved or canonical reply available"
                    )

                return ApprovedResponse(
                    text=text,
                    topic="canonical",
                    source="deterministic_canonical",
                    variant=0,
                    response_id="canonical",
                    role="relative",
                    speaker_label="ΑΓΝΩΣΤΟΣ ΑΡΙΘΜΟΣ",
                    role_handoff=False,
                )

            index = self._variant_index(
                variants,
                stage_id=stage_id,
                topic=selected_topic,
                visitor_text=visitor_text,
                turn=turn,
            )

            return ApprovedResponse(
                text=variants[index].strip(),
                topic=selected_topic,
                source="approved_bank",
                variant=index,
                response_id=(
                    f"{stage_id}:{selected_topic}:{index}"
                ),
                role="relative",
                speaker_label="ΑΓΝΩΣΤΟΣ ΑΡΙΘΜΟΣ",
                role_handoff=False,
            )

        if scenario_id != self.corpus["scenario_id"]:
            return ApprovedResponse(
                text=str(canonical_reply or "").strip(),
                topic="canonical",
                source="deterministic_canonical",
                variant=0,
                response_id="canonical",
                role="unknown",
                speaker_label="ΑΓΝΩΣΤΟΣ ΑΡΙΘΜΟΣ",
                role_handoff=False,
            )

        stage = self.corpus["stages"][stage_id]
        bank = stage["responses"]
        selected_topic = topic if topic in bank else "general"
        variants = bank[selected_topic]

        index = self._variant_index(
            variants,
            stage_id=stage_id,
            topic=selected_topic,
            visitor_text=visitor_text,
            turn=turn,
        )

        text = variants[index].strip()
        handoff = self._is_role_handoff(stage_id)
        intro = str(stage.get("handoff_intro", "")).strip()

        if handoff and intro:
            text = f"{intro} {text}"

        response_id = (
            f"{stage_id}:{selected_topic}:{index}"
        )

        return ApprovedResponse(
            text=text,
            topic=selected_topic,
            source="approved_bank",
            variant=index,
            response_id=response_id,
            role=stage["role"],
            speaker_label=stage["speaker_label"],
            role_handoff=handoff,
        )
