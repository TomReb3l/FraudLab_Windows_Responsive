from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ScenarioValidationError(ValueError):
    pass


class ScenarioEngine:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._payload = self._load()
        self._scenarios = {
            item["scenario_id"]: item for item in self._payload.get("scenarios", [])
        }
        self.validate()

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.data_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ScenarioValidationError(f"Scenario file not found: {self.data_path}") from exc
        except json.JSONDecodeError as exc:
            raise ScenarioValidationError(f"Invalid JSON: {exc}") from exc

    def validate(self) -> None:
        if not self._scenarios:
            raise ScenarioValidationError("No scenarios defined")

        for scenario_id, scenario in self._scenarios.items():
            nodes = scenario.get("nodes", {})
            start_node = scenario.get("start_node")
            if start_node not in nodes:
                raise ScenarioValidationError(
                    f"{scenario_id}: start_node '{start_node}' does not exist"
                )

            for node_id, node in nodes.items():
                if node.get("id") != node_id:
                    raise ScenarioValidationError(
                        f"{scenario_id}: node key '{node_id}' does not match id '{node.get('id')}'"
                    )
                if "choices" not in node or not isinstance(node["choices"], list):
                    raise ScenarioValidationError(
                        f"{scenario_id}/{node_id}: choices must be a list"
                    )
                if node.get("terminal") and node["choices"]:
                    raise ScenarioValidationError(
                        f"{scenario_id}/{node_id}: terminal nodes cannot have choices"
                    )
                for choice in node["choices"]:
                    next_node = choice.get("next_node")
                    if next_node not in nodes:
                        raise ScenarioValidationError(
                            f"{scenario_id}/{node_id}: next_node '{next_node}' does not exist"
                        )

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [
            {
                "scenario_id": s["scenario_id"],
                "type": s["type"],
                "title": s["title"],
                "estimated_seconds": s.get("estimated_seconds"),
            }
            for s in self._scenarios.values()
        ]

    def get_scenario(self, scenario_id: str) -> dict[str, Any]:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:
            raise KeyError(f"Unknown scenario: {scenario_id}") from exc
