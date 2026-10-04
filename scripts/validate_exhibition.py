#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FraudLab exhibition-specific preflight validator.

Read-only. It does not start/stop the exhibition, modify files, or require
pytest/httpx. Exit code 0 means EXHIBITION READY; exit code 1 means NOT READY.
"""

from __future__ import annotations

import asyncio
from collections import Counter, deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_TEXT_EXTENSIONS = {".json", ".py", ".js", ".css", ".html", ".md"}
SKIP_PARTS = {".git", ".venv", "node_modules", "logs", "__pycache__"}
MOJIBAKE_MARKERS = ("β€”", "â€“", "â€”", "â€", "Ã", "Â")

CRITICAL_ROUTES = (
    "/api/health",
    "/",
    "/call",
    "/sms",
    "/qr",
    "/api/scenarios",
    "/api/sms-challenge",
    "/api/qr-challenge",
    "/api/call-audio-manifest",
)

REQUIRED_V6_FILES = (
    "START_FRAUDLAB_EXHIBITION.bat",
    "STOP_FRAUDLAB_EXHIBITION.bat",
    "scripts/exhibition_launcher.py",
    "static/js/call.js",
    "static/js/sms.js",
    "static/js/qr.js",
    "static/sms_sites/index.html",
    "static/qr_sites/common/bridge.js",
)

REQUIRED_FRONTEND_FILES = (
    "frontend/home/index.html",
    "frontend/call/index.html",
    "frontend/sms/index.html",
    "frontend/qr/index.html",
    "static/css/base.css",
    "static/css/home.css",
    "static/css/call.css",
    "static/css/sms.css",
    "static/css/qr.css",
    "static/js/call.js",
    "static/js/sms.js",
    "static/js/qr.js",
)

REQUIRED_UI_AUDIO = (
    "static/audio/ui/incoming_call.mp3",
    "static/audio/ui/incoming_sms.mp3",
    "static/audio/ui/phone_ring.wav",
    "static/audio/ui/sms_notification.wav",
    "static/audio/mail_notification.mp3",
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)

    def section(self, title: str) -> None:
        self.sections.append(title)
        print(f"\n[{len(self.sections)}] {title}")

    def ok(self, message: str) -> None:
        self.passes.append(message)
        print(f"  PASS  {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  WARN  {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"  FAIL  {message}")


class DuplicateKeyError(ValueError):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json_strict(path: Path) -> Any:
    return json.loads(read_utf8(path), object_pairs_hook=_pairs_no_duplicates)


def local_path_from_url(url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path.startswith("/"):
        return None
    return ROOT / parsed.path.lstrip("/")


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def production_text_files() -> list[Path]:
    roots = [ROOT / "backend", ROOT / "data", ROOT / "frontend", ROOT / "static"]
    files: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in PRODUCTION_TEXT_EXTENSIONS:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            files.append(path)
    return files


def check_project_environment(report: Report) -> None:
    report.section("PROJECT / WINDOWS ENVIRONMENT")

    if os.name == "nt":
        report.ok(f"Windows environment detected ({platform.platform()})")
    else:
        report.error(f"Windows exhibition environment required; detected {platform.system()}")

    expected_venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if expected_venv.is_file():
        report.ok(".venv\\Scripts\\python.exe exists")
    else:
        report.error(".venv\\Scripts\\python.exe is missing")

    if os.name == "nt" and expected_venv.is_file():
        try:
            current = Path(sys.executable).resolve()
            expected = expected_venv.resolve()
            if os.path.normcase(str(current)) == os.path.normcase(str(expected)):
                report.ok("Preflight is running from the project .venv")
            else:
                report.error(f"Preflight is not running from project .venv: {current}")
        except OSError as exc:
            report.error(f"Could not verify Python executable: {exc}")

    pyver_file = ROOT / ".python-version"
    if not pyver_file.is_file():
        report.error(".python-version is missing")
    else:
        requested = read_utf8(pyver_file).strip()
        actual = f"{sys.version_info.major}.{sys.version_info.minor}"
        if actual == requested:
            report.ok(f"Python version {actual} matches .python-version")
        else:
            report.error(f"Python {actual} does not match .python-version ({requested})")


def parse_requirement_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
    if not match:
        return None
    return match.group(1), match.group(2)


def check_dependencies(report: Report) -> None:
    report.section("EXHIBITION DEPENDENCIES")
    req = ROOT / "requirements-exhibition.txt"
    if not req.is_file():
        report.error("requirements-exhibition.txt is missing")
        return

    parsed: list[tuple[str, str]] = []
    unsupported: list[str] = []
    for line in read_utf8(req).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = parse_requirement_line(stripped)
        if item is None:
            unsupported.append(stripped)
        else:
            parsed.append(item)

    if unsupported:
        report.error("Unsupported/unpinned exhibition requirements: " + ", ".join(unsupported))

    for package, expected in parsed:
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report.error(f"Missing dependency: {package}=={expected}")
            continue
        if installed != expected:
            report.error(f"Dependency version mismatch: {package} {installed} != {expected}")
        else:
            report.ok(f"{package}=={expected}")


def check_launcher_watchdog(report: Report) -> None:
    report.section("LAUNCHER / WATCHDOG")
    missing = [rel for rel in REQUIRED_V6_FILES if not (ROOT / rel).is_file()]
    if missing:
        for rel in missing:
            report.error(f"Missing v6 reliability file: {rel}")
        return

    launcher = ROOT / "scripts" / "exhibition_launcher.py"
    source = read_utf8(launcher)
    required_markers = (
        'FRAUDLAB_MODE": "exhibition"',
        'ENABLE_AI": "false"',
        'OFFLINE_MODE": "true"',
        'DEBUG_MODE": "false"',
        "WATCHDOG_FAILURE_THRESHOLD = 3",
        "WATCHDOG_MAX_RESTARTS = 3",
        "WATCHDOG_RESTART_WINDOW_SECONDS = 180.0",
        "WATCHDOG_COOLDOWN_SECONDS = 120.0",
        "no unknown process will be terminated",
    )
    for marker in required_markers:
        if marker not in source:
            report.error(f"Launcher/watchdog safety marker missing: {marker}")
    if all(marker in source for marker in required_markers):
        report.ok("Launcher exhibition policy and watchdog safeguards are present")

    try:
        result = subprocess.run(
            [sys.executable, str(launcher), "validate"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
    except Exception as exc:
        report.error(f"Launcher self-validation could not run: {exc}")
        return

    output = result.stdout.strip()
    if result.returncode == 0 and "LAUNCHER READY" in output:
        report.ok("exhibition_launcher.py validate -> LAUNCHER READY")
    else:
        report.error("Launcher self-validation failed: " + (output or f"exit {result.returncode}"))


def forced_exhibition_environment() -> dict[str, str | None]:
    desired = {
        "FRAUDLAB_MODE": "exhibition",
        "ENABLE_AI": "false",
        "OFFLINE_MODE": "true",
        "DEBUG_MODE": "false",
    }
    previous: dict[str, str | None] = {}
    for key, value in desired.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    return previous


def restore_environment(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


async def asgi_get(app: Any, path: str) -> tuple[int, bytes, dict[bytes, bytes]]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"127.0.0.1")],
        "client": ("127.0.0.1", 1),
        "server": ("127.0.0.1", 8000),
    }
    messages: list[dict[str, Any]] = []
    first = True

    async def receive() -> dict[str, Any]:
        nonlocal first
        if first:
            first = False
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.sleep(0)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    starts = [m for m in messages if m["type"] == "http.response.start"]
    if not starts:
        raise RuntimeError(f"No ASGI response start for {path}")
    status = int(starts[0]["status"])
    headers = {k.lower(): v for k, v in starts[0].get("headers", [])}
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, body, headers


def import_exhibition_app(report: Report) -> Any | None:
    previous = forced_exhibition_environment()
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        for name in list(sys.modules):
            if name == "backend.config" or name == "backend.main":
                sys.modules.pop(name, None)

        from backend import config
        from backend.main import app

        if not config.is_exhibition_mode():
            report.error("backend.config is not in exhibition mode under forced policy")
        elif config.is_ai_enabled():
            report.error("AI is enabled under forced exhibition policy")
        elif not bool(config.OFFLINE_MODE):
            report.error("OFFLINE_MODE is false under forced exhibition policy")
        elif bool(config.DEBUG_MODE):
            report.error("DEBUG_MODE is true under forced exhibition policy")
        else:
            report.ok("Backend forced policy: exhibition / offline / AI disabled / debug disabled")

        ai_routes = [
            getattr(route, "path", "")
            for route in app.routes
            if str(getattr(route, "path", "")).startswith("/api/ai")
        ]
        if ai_routes:
            report.error("AI API routes are loaded in exhibition mode: " + ", ".join(ai_routes))
        else:
            report.ok("AI API router is not loaded in exhibition mode")

        return app
    except Exception as exc:
        report.error(f"FastAPI app import failed: {type(exc).__name__}: {exc}")
        return None
    finally:
        restore_environment(previous)


def check_fastapi_routes(report: Report) -> None:
    report.section("FASTAPI / EXHIBITION POLICY / CRITICAL ROUTES")
    app = import_exhibition_app(report)
    if app is None:
        return

    for path in CRITICAL_ROUTES:
        try:
            status, body, _headers = asyncio.run(asgi_get(app, path))
        except Exception as exc:
            report.error(f"{path}: ASGI request failed: {type(exc).__name__}: {exc}")
            continue

        if status != 200:
            report.error(f"{path}: HTTP {status}")
            continue

        if path == "/api/health":
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as exc:
                report.error(f"/api/health: invalid JSON: {exc}")
                continue
            good = (
                isinstance(payload, dict)
                and str(payload.get("status", "")).lower() == "ok"
                and str(payload.get("mode", "")).lower() == "offline-first"
                and str(payload.get("ai_enabled", "")).lower() == "false"
            )
            if not good:
                report.error(f"/api/health does not match exhibition policy: {payload}")
                continue

        report.ok(f"{path} -> 200")


def check_utf8_json(report: Report) -> None:
    report.section("UTF-8 / JSON / ENCODING")
    json_count = 0
    utf8_count = 0
    question_corruption: list[str] = []
    mojibake: list[str] = []

    for path in production_text_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = read_utf8(path)
        except UnicodeDecodeError as exc:
            report.error(f"UTF-8 decode failed: {rel}: {exc}")
            continue
        except OSError as exc:
            report.error(f"Could not read {rel}: {exc}")
            continue

        utf8_count += 1
        if "????" in text:
            question_corruption.append(rel)
        if any(marker in text for marker in MOJIBAKE_MARKERS):
            mojibake.append(rel)

        if path.suffix.lower() == ".json":
            json_count += 1
            try:
                load_json_strict(path)
            except Exception as exc:
                report.error(f"JSON validation failed: {rel}: {exc}")

    if question_corruption:
        for rel in question_corruption:
            report.error(f'Possible Greek corruption "????": {rel}')
    else:
        report.ok('No "????" corruption markers detected')

    if mojibake:
        for rel in sorted(set(mojibake)):
            report.warn(f"Possible legacy mojibake marker: {rel}")
    else:
        report.ok("No common mojibake markers detected")

    report.ok(f"UTF-8 scanned {utf8_count} production text files")
    report.ok(f"Strict JSON parsed {json_count} files")


def require_item_fields(report: Report, prefix: str, item: dict[str, Any], required: tuple[str, ...]) -> bool:
    ok = True
    for field_name in required:
        value = item.get(field_name)
        if value is None or value == "" or value == [] or value == {}:
            report.error(f"{prefix}: missing/empty field {field_name!r}")
            ok = False
    return ok


def reachable_nodes(nodes: dict[str, Any], start: str) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node_id = queue.popleft()
        if node_id in seen or node_id not in nodes:
            continue
        seen.add(node_id)
        for choice in nodes[node_id].get("choices", []):
            nxt = choice.get("next_node")
            if isinstance(nxt, str) and nxt not in seen:
                queue.append(nxt)
    return seen


def nodes_that_can_reach_terminal(nodes: dict[str, Any]) -> set[str]:
    good = {node_id for node_id, node in nodes.items() if node.get("terminal") is True}
    changed = True
    while changed:
        changed = False
        for node_id, node in nodes.items():
            if node_id in good:
                continue
            if any(choice.get("next_node") in good for choice in node.get("choices", [])):
                good.add(node_id)
                changed = True
    return good


def check_call_scenarios(report: Report) -> None:
    report.section("CALL SCENARIOS")
    path = ROOT / "data" / "call_scenarios.json"
    try:
        payload = load_json_strict(path)
    except Exception as exc:
        report.error(f"Cannot validate call_scenarios.json: {exc}")
        return

    scenarios = payload.get("scenarios") if isinstance(payload, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        report.error("call_scenarios.json: scenarios must be a non-empty list")
        return

    scenario_ids: list[str] = []
    audio_refs = 0

    for index, scenario in enumerate(scenarios):
        prefix = f"call scenario #{index + 1}"
        if not isinstance(scenario, dict):
            report.error(f"{prefix}: scenario must be an object")
            continue
        require_item_fields(report, prefix, scenario, ("scenario_id", "type", "title", "start_node", "nodes", "educational_message"))
        scenario_id = scenario.get("scenario_id")
        if not nonempty_text(scenario_id):
            continue
        scenario_ids.append(scenario_id)
        prefix = scenario_id

        nodes = scenario.get("nodes")
        start = scenario.get("start_node")
        if not isinstance(nodes, dict) or not nodes:
            report.error(f"{prefix}: nodes must be a non-empty object")
            continue
        if start not in nodes:
            report.error(f"{prefix}: start_node {start!r} does not exist")
            continue

        for node_id, node in nodes.items():
            np = f"{prefix}/{node_id}"
            if not isinstance(node, dict):
                report.error(f"{np}: node must be an object")
                continue
            if node.get("id") != node_id:
                report.error(f"{np}: node key does not match node.id={node.get('id')!r}")
            if not nonempty_text(node.get("text")):
                report.error(f"{np}: missing/empty text")
            choices = node.get("choices")
            if not isinstance(choices, list):
                report.error(f"{np}: choices must be a list")
                continue
            terminal = node.get("terminal")
            if not isinstance(terminal, bool):
                report.error(f"{np}: terminal must be boolean")
            if terminal is True and choices:
                report.error(f"{np}: terminal node contains choices")
            if terminal is False and not choices:
                report.error(f"{np}: non-terminal node has no choices")
            if terminal is True:
                if not nonempty_list(node.get("red_flags")):
                    report.error(f"{np}: terminal result is missing red_flags")
                if not nonempty_text(node.get("safe_action")):
                    report.error(f"{np}: terminal result is missing safe_action")

            if "score_delta" in node and not is_number(node["score_delta"]):
                report.error(f"{np}: node score_delta must be numeric")

            audio = node.get("audio")
            if audio is not None:
                if not nonempty_text(audio):
                    report.error(f"{np}: audio must be a non-empty local path")
                else:
                    audio_refs += 1
                    local = local_path_from_url(audio)
                    if local is None:
                        report.error(f"{np}: audio is not a local absolute path: {audio}")
                    elif not local.is_file():
                        report.error(f"{np}: missing audio asset {audio}")

            for cidx, choice in enumerate(choices):
                cp = f"{np}/choice[{cidx}]"
                if not isinstance(choice, dict):
                    report.error(f"{cp}: choice must be an object")
                    continue
                for field_name in ("label", "next_node", "intent"):
                    if not nonempty_text(choice.get(field_name)):
                        report.error(f"{cp}: missing/empty {field_name}")
                if not is_number(choice.get("score_delta")):
                    report.error(f"{cp}: score_delta must be numeric")
                nxt = choice.get("next_node")
                if isinstance(nxt, str) and nxt not in nodes:
                    report.error(f"{cp}: next_node {nxt!r} does not exist")

        reachable = reachable_nodes(nodes, start)
        unreachable = sorted(set(nodes) - reachable)
        if unreachable:
            report.warn(f"{prefix}: {len(unreachable)} node(s) are not reachable by plain next_node traversal: " + ", ".join(unreachable))
        else:
            report.ok(f"{prefix}: all {len(nodes)} nodes reachable from {start}")

        can_finish = nodes_that_can_reach_terminal(nodes)
        stuck = sorted(reachable - can_finish)
        if stuck:
            report.error(f"{prefix}: reachable node(s) cannot reach any terminal result: " + ", ".join(stuck))
        else:
            report.ok(f"{prefix}: every reachable node can reach a terminal result")

    duplicates = sorted(k for k, count in Counter(scenario_ids).items() if count > 1)
    if duplicates:
        report.error("Duplicate Call scenario_id values: " + ", ".join(duplicates))
    else:
        report.ok(f"Call scenarios: {len(scenario_ids)} unique scenario IDs")
    report.ok(f"Call node audio references checked: {audio_refs}")


def check_choice_list(report: Report, prefix: str, choices: Any) -> None:
    if not isinstance(choices, list) or not choices:
        report.error(f"{prefix}: choices must be a non-empty list")
        return
    safe_values: set[bool] = set()
    for index, choice in enumerate(choices):
        cp = f"{prefix}/choice[{index}]"
        if not isinstance(choice, dict):
            report.error(f"{cp}: choice must be an object")
            continue
        if not nonempty_text(choice.get("label")):
            report.error(f"{cp}: missing/empty label")
        if not is_number(choice.get("score")):
            report.error(f"{cp}: score must be numeric")
        if not isinstance(choice.get("safe"), bool):
            report.error(f"{cp}: safe must be boolean")
        else:
            safe_values.add(choice["safe"])
        if not nonempty_text(choice.get("feedback")):
            report.error(f"{cp}: missing/empty feedback")
    if safe_values != {False, True}:
        report.warn(f"{prefix}: choices do not include both safe and unsafe outcomes")


def check_sms_scenarios(report: Report) -> None:
    report.section("SMS / PHISHING SCENARIOS")
    path = ROOT / "data" / "sms_scenarios.json"
    try:
        payload = load_json_strict(path)
    except Exception as exc:
        report.error(f"Cannot validate sms_scenarios.json: {exc}")
        return
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        report.error("sms_scenarios.json: items must be a non-empty list")
        return
    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            report.error("SMS item must be an object")
            continue
        item_id = item.get("id")
        prefix = f"SMS/{item_id or '?'}"
        require_item_fields(report, prefix, item, ("id", "category", "sender", "time", "message", "choices", "red_flags", "safe_action"))
        if nonempty_text(item_id):
            ids.append(item_id)
        if not nonempty_list(item.get("red_flags")):
            report.error(f"{prefix}: red_flags must be a non-empty list")
        if not nonempty_text(item.get("safe_action")):
            report.error(f"{prefix}: safe_action is missing")
        check_choice_list(report, prefix, item.get("choices"))
        simulation_url = item.get("simulation_url")
        if simulation_url:
            local = local_path_from_url(simulation_url)
            if local is None:
                report.error(f"{prefix}: simulation_url is not local: {simulation_url}")
            elif not local.is_file():
                report.error(f"{prefix}: missing simulation file {simulation_url}")
    duplicates = sorted(k for k, count in Counter(ids).items() if count > 1)
    if duplicates:
        report.error("Duplicate SMS item IDs: " + ", ".join(duplicates))
    else:
        report.ok(f"SMS scenarios: {len(ids)} unique item IDs")


def check_qr_scenarios(report: Report) -> None:
    report.section("EMAIL / QR SCENARIOS")
    path = ROOT / "data" / "qr_scenarios.json"
    try:
        payload = load_json_strict(path)
    except Exception as exc:
        report.error(f"Cannot validate qr_scenarios.json: {exc}")
        return
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        report.error("qr_scenarios.json: items must be a non-empty list")
        return
    ids: list[str] = []
    qr_pairs = 0
    for item in items:
        if not isinstance(item, dict):
            report.error("QR item must be an object")
            continue
        item_id = item.get("id")
        prefix = f"QR/{item_id or '?'}"
        require_item_fields(report, prefix, item, ("id", "category", "email", "subject", "poster_title", "poster_text", "site_name", "choices", "red_flags", "safe_action", "qr_image", "simulation_url"))
        if nonempty_text(item_id):
            ids.append(item_id)
        email = item.get("email")
        if not isinstance(email, dict):
            report.error(f"{prefix}: email must be an object")
        else:
            require_item_fields(report, f"{prefix}/email", email, ("from_name", "from_address", "subject", "received_time", "body_lines"))
            if not isinstance(email.get("body_lines"), list) or not email.get("body_lines"):
                report.error(f"{prefix}/email: body_lines must be a non-empty list")
        if not nonempty_list(item.get("red_flags")):
            report.error(f"{prefix}: red_flags must be a non-empty list")
        if not nonempty_text(item.get("safe_action")):
            report.error(f"{prefix}: safe_action is missing")
        check_choice_list(report, prefix, item.get("choices"))
        qr_image = item.get("qr_image")
        if nonempty_text(qr_image):
            image_path = local_path_from_url(qr_image)
            if image_path is None:
                report.error(f"{prefix}: qr_image is not local: {qr_image}")
            elif not image_path.is_file():
                report.error(f"{prefix}: missing QR image {qr_image}")
            else:
                print_copy = ROOT / "QR_PRINT" / (image_path.stem.upper() + image_path.suffix)
                if not print_copy.is_file():
                    report.error(f"{prefix}: missing printable QR copy QR_PRINT/{image_path.stem.upper() + image_path.suffix}")
                elif image_path.read_bytes() != print_copy.read_bytes():
                    report.error(f"{prefix}: static QR and QR_PRINT copy are not byte-identical")
                else:
                    qr_pairs += 1
        simulation_url = item.get("simulation_url")
        if nonempty_text(simulation_url):
            local = local_path_from_url(simulation_url)
            if local is None:
                report.error(f"{prefix}: simulation_url is not local: {simulation_url}")
            elif not local.is_file():
                report.error(f"{prefix}: missing local fake-site {simulation_url}")
    duplicates = sorted(k for k, count in Counter(ids).items() if count > 1)
    if duplicates:
        report.error("Duplicate QR item IDs: " + ", ".join(duplicates))
    else:
        report.ok(f"QR scenarios: {len(ids)} unique item IDs")
    report.ok(f"QR printable/static byte-identical pairs checked: {qr_pairs}")


def check_audio_manifest(report: Report) -> None:
    report.section("AUDIO MANIFEST / AUDIO ASSETS")
    path = ROOT / "data" / "call_audio_manifest.json"
    try:
        manifest = load_json_strict(path)
        call_payload = load_json_strict(ROOT / "data" / "call_scenarios.json")
    except Exception as exc:
        report.error(f"Audio validation data unavailable: {exc}")
        return
    scenario_map = {s.get("scenario_id"): s for s in call_payload.get("scenarios", []) if isinstance(s, dict) and nonempty_text(s.get("scenario_id"))}
    checked_scene_audio = 0
    checked_mappings = 0
    if not isinstance(manifest, dict):
        report.error("call_audio_manifest.json must contain an object")
        return
    for scenario_id, config in manifest.items():
        if scenario_id not in scenario_map:
            report.error(f"Audio manifest references unknown scenario: {scenario_id}")
            continue
        if not isinstance(config, dict):
            report.error(f"Audio manifest {scenario_id}: config must be an object")
            continue
        scenes = config.get("scenes")
        nodes_map = config.get("nodes")
        default_scene = config.get("default_scene")
        if not isinstance(scenes, dict) or not scenes:
            report.error(f"Audio manifest {scenario_id}: scenes must be non-empty")
            continue
        if default_scene not in scenes:
            report.error(f"Audio manifest {scenario_id}: default_scene {default_scene!r} is missing")
        if not isinstance(nodes_map, dict):
            report.error(f"Audio manifest {scenario_id}: nodes must be an object")
            continue
        for scene_id, scene in scenes.items():
            if not isinstance(scene, dict) or not nonempty_text(scene.get("audio")):
                report.error(f"Audio manifest {scenario_id}/{scene_id}: missing audio path")
                continue
            local = local_path_from_url(scene["audio"])
            if local is None or not local.is_file():
                report.error(f"Audio manifest {scenario_id}/{scene_id}: missing audio asset {scene['audio']}")
            else:
                checked_scene_audio += 1
        scenario_nodes = scenario_map[scenario_id].get("nodes", {})
        for node_id, scene_id in nodes_map.items():
            if node_id not in scenario_nodes:
                report.error(f"Audio manifest {scenario_id}: mapping references unknown node {node_id}")
            if scene_id not in scenes:
                report.error(f"Audio manifest {scenario_id}/{node_id}: unknown scene {scene_id}")
            checked_mappings += 1
    for rel in REQUIRED_UI_AUDIO:
        if not (ROOT / rel).is_file():
            report.error(f"Missing UI audio asset: {rel}")
    report.ok(f"Ambient scene audio files checked: {checked_scene_audio}")
    report.ok(f"Ambient node mappings checked: {checked_mappings}")
    if all((ROOT / rel).is_file() for rel in REQUIRED_UI_AUDIO):
        report.ok(f"Required UI audio assets checked: {len(REQUIRED_UI_AUDIO)}")


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.lower() == "id" and value:
                self.ids.append(value)


def html_asset_refs(text: str) -> list[str]:
    return re.findall(r"(?:src|href)\s*=\s*['\"]([^'\"]+)['\"]", text, flags=re.I)


def check_frontend_assets(report: Report) -> None:
    report.section("FRONTEND / STATIC / OFFLINE ASSETS")
    for rel in REQUIRED_FRONTEND_FILES:
        if not (ROOT / rel).is_file():
            report.error(f"Missing required frontend file: {rel}")
    html_files = list((ROOT / "frontend").rglob("*.html"))
    html_files += list((ROOT / "static" / "qr_sites").rglob("*.html"))
    sms_html = ROOT / "static" / "sms_sites" / "index.html"
    if sms_html.is_file():
        html_files.append(sms_html)
    asset_refs_checked = 0
    for path in html_files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = read_utf8(path)
        except Exception as exc:
            report.error(f"Could not read HTML {rel}: {exc}")
            continue
        parser = IdCollector()
        try:
            parser.feed(text)
        except Exception as exc:
            report.error(f"HTML parser failed for {rel}: {exc}")
        duplicates = sorted(k for k, count in Counter(parser.ids).items() if count > 1)
        if duplicates:
            report.error(f"{rel}: duplicate DOM id(s): " + ", ".join(duplicates))
        for ref in html_asset_refs(text):
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc:
                continue
            if parsed.path.startswith("/static/"):
                local = ROOT / parsed.path.lstrip("/")
                asset_refs_checked += 1
                if not local.is_file():
                    report.error(f"{rel}: missing referenced asset {parsed.path}")
    code_files = [
        *ROOT.joinpath("frontend").rglob("*.html"),
        *ROOT.joinpath("static").rglob("*.html"),
        *ROOT.joinpath("static").rglob("*.js"),
        *ROOT.joinpath("static").rglob("*.css"),
    ]
    remote_hits: list[str] = []
    patterns = (
        re.compile(r"<script\b[^>]*\bsrc\s*=\s*['\"]https?://", re.I),
        re.compile(r"<link\b[^>]*\bhref\s*=\s*['\"]https?://", re.I),
        re.compile(r"@import\s+(?:url\()?['\"]?https?://", re.I),
        re.compile(r"fetch\s*\(\s*['\"]https?://", re.I),
        re.compile(r"new\s+WebSocket\s*\(\s*['\"]wss?://", re.I),
    )
    for path in code_files:
        try:
            text = read_utf8(path)
        except Exception:
            continue
        if any(pattern.search(text) for pattern in patterns):
            remote_hits.append(path.relative_to(ROOT).as_posix())
    if remote_hits:
        for rel in sorted(set(remote_hits)):
            report.error(f"External runtime dependency detected: {rel}")
    else:
        report.ok("No remote script/link/import/fetch dependencies detected")
    if all((ROOT / rel).is_file() for rel in REQUIRED_FRONTEND_FILES):
        report.ok(f"Required frontend/static files checked: {len(REQUIRED_FRONTEND_FILES)}")
    report.ok(f"Local /static asset references checked: {asset_refs_checked}")


def check_visitor_reset(report: Report) -> None:
    report.section("AUTOMATIC VISITOR RESET")
    files = {"Call": ROOT / "static/js/call.js", "SMS": ROOT / "static/js/sms.js", "QR": ROOT / "static/js/qr.js"}
    for station, path in files.items():
        if not path.is_file():
            report.error(f"{station}: visitor reset JS file missing")
            continue
        source = read_utf8(path)
        markers = ("const IDLE_WARNING_MS = 65000;", "const IDLE_RESET_MS = 75000;", "window.location.replace('/')")
        missing = [marker for marker in markers if marker not in source]
        if missing:
            report.error(f"{station}: visitor reset marker(s) missing: " + ", ".join(missing))
        else:
            report.ok(f"{station}: 65s warning / 75s home reset present")
    sms = ROOT / "static/js/sms.js"
    qr = ROOT / "static/js/qr.js"
    sms_site = ROOT / "static/sms_sites/index.html"
    qr_bridge = ROOT / "static/qr_sites/common/bridge.js"
    checks = (
        ("SMS parent activity receiver", sms, "fraudlab:simulation-activity"),
        ("QR parent activity receiver", qr, "fraudlab:simulation-activity"),
        ("SMS fake-site activity sender", sms_site, "postParent('fraudlab:simulation-activity')"),
        ("QR fake-site activity sender", qr_bridge, "post('fraudlab:simulation-activity')"),
    )
    for label, path, marker in checks:
        if not path.is_file():
            report.error(f"{label}: file missing {path.relative_to(ROOT)}")
        elif marker not in read_utf8(path):
            report.error(f"{label}: marker missing")
        else:
            report.ok(label)
    if sms.is_file():
        source = read_utf8(sms)
        if "SIMULATION_MAX_MS" in source or "simulationTimer" in source:
            report.error("SMS legacy fixed simulation timeout is still present")
    if qr.is_file():
        source = read_utf8(qr)
        if "QR_SIMULATION_MAX_MS" in source or "qrSimulationTimer" in source:
            report.error("QR legacy fixed simulation timeout is still present")


def check_known_test_baseline(report: Report) -> None:
    report.section("KNOWN BASELINE WARNINGS")
    test_file = ROOT / "tests" / "test_scenario_engine.py"
    if test_file.is_file():
        text = read_utf8(test_file)
        if re.search(r"assert\s+len\(scenarios\)\s*==\s*1", text):
            report.warn("tests/test_scenario_engine.py still expects exactly 1 Call scenario; this is stale relative to the current 2-scenario exhibition data and is not a readiness blocker")
        else:
            report.ok("No stale single-Call-scenario assertion detected")
    else:
        report.warn("tests/test_scenario_engine.py is missing; pytest baseline check not available")


def final_summary(report: Report) -> int:
    print("\n" + "=" * 68)
    print("EXHIBITION NOT READY" if report.errors else "EXHIBITION READY")
    print(f"Errors:   {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Passes:   {len(report.passes)}")
    if report.errors:
        print("\nBlocking errors:")
        for index, item in enumerate(report.errors, start=1):
            print(f"  {index}. {item}")
    if report.warnings:
        print("\nWarnings / review items:")
        for index, item in enumerate(report.warnings, start=1):
            print(f"  {index}. {item}")
    print("=" * 68)
    return 1 if report.errors else 0


def main() -> int:
    report = Report()
    check_project_environment(report)
    check_dependencies(report)
    check_launcher_watchdog(report)
    check_fastapi_routes(report)
    check_utf8_json(report)
    check_call_scenarios(report)
    check_sms_scenarios(report)
    check_qr_scenarios(report)
    check_audio_manifest(report)
    check_frontend_assets(report)
    check_visitor_reset(report)
    check_known_test_baseline(report)
    return final_summary(report)


if __name__ == "__main__":
    raise SystemExit(main())
