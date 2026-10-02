from pathlib import Path

from backend.scenario_engine import ScenarioEngine


BASE_DIR = Path(__file__).resolve().parents[1]


def test_scenario_file_validates():
    engine = ScenarioEngine(BASE_DIR / "data" / "call_scenarios.json")
    scenarios = engine.list_scenarios()
    assert len(scenarios) == 1
    assert scenarios[0]["scenario_id"] == "call_account_security_001"


def test_all_non_terminal_choices_point_to_existing_nodes():
    engine = ScenarioEngine(BASE_DIR / "data" / "call_scenarios.json")
    scenario = engine.get_scenario("call_account_security_001")
    nodes = scenario["nodes"]

    for node in nodes.values():
        for choice in node["choices"]:
            assert choice["next_node"] in nodes


def test_all_nodes_are_reachable_and_terminal_path_exists():
    engine = ScenarioEngine(BASE_DIR / "data" / "call_scenarios.json")
    scenario = engine.get_scenario("call_account_security_001")
    nodes = scenario["nodes"]
    seen = set()
    stack = [scenario["start_node"]]

    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        stack.extend(choice["next_node"] for choice in nodes[node_id]["choices"])

    assert seen == set(nodes)
    assert any(nodes[node_id]["terminal"] for node_id in seen)


def test_all_declared_audio_assets_exist():
    engine = ScenarioEngine(BASE_DIR / "data" / "call_scenarios.json")
    scenario = engine.get_scenario("call_account_security_001")
    for node in scenario["nodes"].values():
        audio = node.get("audio")
        if audio:
            relative = audio.removeprefix("/static/")
            assert (BASE_DIR / "static" / relative).is_file()
