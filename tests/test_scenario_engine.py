from pathlib import Path

from backend.scenario_engine import ScenarioEngine


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "call_scenarios.json"
EXPECTED_SCENARIO_IDS = {
    "call_account_security_001",
    "call_accident_police_001",
}


def _engine() -> ScenarioEngine:
    return ScenarioEngine(DATA_FILE)


def test_scenario_file_validates():
    scenarios = _engine().list_scenarios()
    assert len(scenarios) == 2
    assert {item["scenario_id"] for item in scenarios} == EXPECTED_SCENARIO_IDS


def test_all_non_terminal_choices_point_to_existing_nodes():
    engine = _engine()
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = engine.get_scenario(scenario_id)
        nodes = scenario["nodes"]
        for node in nodes.values():
            for choice in node["choices"]:
                assert choice["next_node"] in nodes


def test_each_scenario_has_a_reachable_terminal_path():
    engine = _engine()
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = engine.get_scenario(scenario_id)
        nodes = scenario["nodes"]
        seen = set()
        stack = [scenario["start_node"]]

        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            stack.extend(choice["next_node"] for choice in nodes[node_id]["choices"])

        assert seen
        assert any(nodes[node_id]["terminal"] for node_id in seen)


def test_all_declared_audio_assets_exist():
    engine = _engine()
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = engine.get_scenario(scenario_id)
        for node in scenario["nodes"].values():
            audio = node.get("audio")
            if audio:
                relative = audio.removeprefix("/static/")
                assert (BASE_DIR / "static" / relative).is_file()
