from __future__ import annotations

import argparse
import compileall
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_NAME = "call_mobile_v1"

CALL_MOBILE_CSS = r'''/*
 FRAUD LAB — Call Station Mobile Overrides
 Phase 1 · Telephone Fraud only

 Loaded after call.css. Rules apply only at <= 768px so the
 desktop/exhibition presentation remains unchanged.
*/

@media (max-width: 768px) {
  body.call-page .app-shell {
    min-height: 100vh;
    min-height: 100dvh;
  }

  body.call-page .screen,
  body.call-page #screen[data-call-mode="result"] {
    width: calc(100% - 20px);
    max-width: 100%;
    padding: 18px 0 28px;
    align-items: flex-start;
  }

  body.call-page .experience-card,
  body.call-page #screen[data-call-mode="result"] .experience-card {
    width: 100%;
    max-width: 100%;
  }

  body.call-page .hero-panel {
    min-height: 0;
    padding: 28px 20px;
  }

  body.call-page .hero-panel h1 {
    margin: 14px auto 16px;
    font-size: clamp(2rem, 9vw, 3rem);
    line-height: 1.05;
  }

  body.call-page .hero-panel p {
    margin-bottom: 24px;
    font-size: clamp(1rem, 3.8vw, 1.14rem);
  }

  body.call-page .scenario-select-wrapper {
    display: block;
    width: min(100%, 520px);
    max-width: 100%;
  }

  body.call-page #scenarioSelect,
  body.call-page .scenario-select-wrapper #scenarioSelect {
    width: 100%;
    min-width: 0;
    max-width: 100%;
    height: auto;
    min-height: 54px;
    padding: 10px 42px 10px 14px;
    white-space: normal;
  }

  body.call-page .phone-stage {
    padding: 20px;
    gap: 18px;
  }

  body.call-page .phone-shell {
    min-height: 340px;
    padding: 24px 20px;
  }

  body.call-page .dialogue-panel {
    padding: 20px;
  }

  body.call-page .phone-stage .dialogue-text {
    font-size: clamp(1.35rem, 5.8vw, 1.75rem);
    line-height: 1.15;
    overflow-wrap: anywhere;
  }

  body.call-page .choice-button {
    min-height: 64px;
    padding: 14px 16px;
    font-size: clamp(1rem, 3.8vw, 1.12rem);
  }

  body.call-page #screen[data-call-mode="result"] .result-card {
    padding: 22px 20px;
  }

  body.call-page #screen[data-call-mode="result"] .result-card h1 {
    width: 100%;
    max-width: 100%;
    margin: 14px 0 10px;
    font-size: clamp(1.8rem, 7.8vw, 2.5rem);
    line-height: 1.08;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  body.call-page #screen[data-call-mode="result"] .result-card > p {
    font-size: 1rem;
    line-height: 1.5;
  }

  body.call-page #screen[data-call-mode="result"] .score-panel,
  body.call-page #screen[data-call-mode="result"] .red-flags,
  body.call-page #screen[data-call-mode="result"] .lesson-grid {
    margin: 12px 0;
  }

  body.call-page #screen[data-call-mode="result"] .lesson-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }

  body.call-page #screen[data-call-mode="result"] .lesson {
    min-height: 0;
    padding: 16px;
  }

  body.call-page #screen[data-call-mode="result"] .unsafe-help-line1,
  body.call-page #screen[data-call-mode="result"] .unsafe-help-line2 {
    max-width: 100%;
    font-size: clamp(1.45rem, 6.5vw, 2rem);
    line-height: 1.12;
    overflow-wrap: anywhere;
  }

  body.call-page #screen[data-call-mode="result"] .unsafe-help-subtext {
    max-width: 100%;
    font-size: 1rem;
  }

  body.call-page #screen[data-call-mode="result"] .result-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 16px;
  }

  body.call-page #screen[data-call-mode="result"] .result-actions > button {
    width: 100%;
    min-height: 56px;
  }

  body.call-page .footer-strip {
    min-height: 0;
    gap: 8px;
    padding: 14px 12px;
    font-size: clamp(.86rem, 3.6vw, 1rem);
  }

  body.call-page .timeout-modal {
    padding: 14px;
  }

  body.call-page .timeout-card {
    padding: 22px 18px;
  }

  body.call-page .timeout-card h2 {
    font-size: clamp(1.45rem, 7vw, 2rem);
  }

  body.call-page .timeout-card p {
    font-size: 1rem;
  }

  body.call-page .timeout-card .primary-button {
    width: 100%;
  }
}

@media (max-width: 480px) {
  body.call-page .topbar {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: max(14px, env(safe-area-inset-top)) 14px 14px;
  }

  body.call-page .brand-block,
  body.call-page .top-actions {
    width: 100%;
    min-width: 0;
  }

  body.call-page .top-actions {
    gap: 8px;
  }

  body.call-page .ghost-button {
    width: 100%;
    min-height: 48px;
    white-space: normal;
  }

  body.call-page .screen,
  body.call-page #screen[data-call-mode="result"] {
    width: calc(100% - 16px);
  }

  body.call-page .hero-panel,
  body.call-page .phone-stage,
  body.call-page .dialogue-panel,
  body.call-page #screen[data-call-mode="result"] .result-card {
    padding-left: 18px;
    padding-right: 18px;
  }

  body.call-page .phone-shell {
    min-height: 320px;
    padding: 22px 18px;
  }

  body.call-page .call-indicator {
    width: 74px;
    height: 74px;
    margin-top: 26px;
  }

  body.call-page .result-badge {
    max-width: 100%;
    font-size: .88rem;
    line-height: 1.3;
    text-align: center;
  }
}
'''

EXPECTED_FILES = (
    "frontend/home/index.html",
    "static/css/mobile.css",
    "frontend/call/index.html",
    "static/css/base.css",
    "static/css/call.css",
    "static/js/call.js",
    "backend/main.py",
    "data/call_scenarios.json",
    "frontend/sms/index.html",
    "frontend/qr/index.html",
)

RESPONSIVE_BASELINE_MARKER = '/static/css/mobile.css?v=1.0'

CALL_CSS_LINK = '  <link rel="stylesheet" href="/static/css/call.css?v=8.0">'
CALL_MOBILE_LINK = '  <link rel="stylesheet" href="/static/css/call-mobile.css?v=1.0">'
CALL_SCRIPT_OLD = '  <script src="/static/js/call.js?v=8.5" defer></script>'
CALL_SCRIPT_NEW = '  <script src="/static/js/call.js?v=8.6" defer></script>'

SET_MODE_OLD = """  function setCallMode(mode) {\n    screen.dataset.callMode = mode;\n  }"""
SET_MODE_NEW = """  function setCallMode(mode) {\n    screen.dataset.callMode = mode;\n\n    // Mobile pages are taller than the exhibition viewport. Each newly\n    // rendered step should begin at the station header instead of inheriting\n    // the scroll position of the previous choice. Desktop remains unchanged.\n    if (window.matchMedia('(max-width: 768px)').matches) {\n      window.scrollTo(0, 0);\n    }\n  }"""


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(code)


def project_root() -> Path:
    return Path.cwd().resolve()


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"UTF-8 decode failed for {path}: {exc}")


def check_root(project: Path) -> None:
    missing = [rel for rel in EXPECTED_FILES if not (project / rel).is_file()]
    if missing:
        fail(
            "This does not look like the FraudLab responsive project root. Missing: "
            + ", ".join(missing)
        )

    home_text = read_utf8(project / "frontend/home/index.html")
    if RESPONSIVE_BASELINE_MARKER not in home_text:
        fail(
            "Responsive Home baseline marker is missing. Refusing to patch the stable/original repo."
        )


def backup_root(project: Path) -> Path:
    return project.parent / f"{project.name}_backups" / "call_mobile"


def create_backup(project: Path, purpose: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(project) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    targets = {
        "call_index.html": project / "frontend/call/index.html",
        "call.js": project / "static/js/call.js",
        "call-mobile.css": project / "static/css/call-mobile.css",
    }

    existed: dict[str, bool] = {}
    for backup_name, source in targets.items():
        existed[backup_name] = source.exists()
        if source.exists():
            shutil.copy2(source, dest / backup_name)

    manifest = {
        "patch": PATCH_NAME,
        "purpose": purpose,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "files_existed": existed,
        "rolled_back": False,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"BACKUP: {dest}")
    return dest


def detect_state(project: Path) -> str:
    html = read_utf8(project / "frontend/call/index.html")
    js = read_utf8(project / "static/js/call.js")
    css_path = project / "static/css/call-mobile.css"

    patched = (
        CALL_MOBILE_LINK in html
        and CALL_SCRIPT_NEW in html
        and CALL_SCRIPT_OLD not in html
        and SET_MODE_NEW in js
        and SET_MODE_OLD not in js
        and css_path.is_file()
        and read_utf8(css_path) == CALL_MOBILE_CSS
    )
    if patched:
        return "patched"

    original = (
        CALL_CSS_LINK in html
        and CALL_MOBILE_LINK not in html
        and CALL_SCRIPT_OLD in html
        and CALL_SCRIPT_NEW not in html
        and SET_MODE_OLD in js
        and SET_MODE_NEW not in js
        and not css_path.exists()
    )
    if original:
        return "original"

    return "unexpected"


def validate_json_and_python(project: Path) -> None:
    bad_markers: list[str] = []
    bad_json: list[str] = []

    for path in project.rglob("*.json"):
        text = read_utf8(path)
        if "????" in text:
            bad_markers.append(str(path.relative_to(project)))
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            bad_json.append(f"{path.relative_to(project)}: {exc}")

    if bad_markers:
        fail("Encoding corruption marker found in JSON: " + ", ".join(bad_markers))
    if bad_json:
        fail("Invalid JSON: " + " | ".join(bad_json))

    if not compileall.compile_dir(str(project / "backend"), quiet=1):
        fail("Python compile validation failed under backend/")


def validate_static(project: Path) -> None:
    html = read_utf8(project / "frontend/call/index.html")
    js = read_utf8(project / "static/js/call.js")
    css_path = project / "static/css/call-mobile.css"

    if CALL_MOBILE_LINK not in html:
        fail("Call validation failed: call-mobile.css link is missing")
    if CALL_SCRIPT_NEW not in html or CALL_SCRIPT_OLD in html:
        fail("Call validation failed: call.js cache version is not v8.6")

    call_css_pos = html.find(CALL_CSS_LINK)
    mobile_css_pos = html.find(CALL_MOBILE_LINK)
    if call_css_pos < 0 or mobile_css_pos <= call_css_pos:
        fail("Call validation failed: call-mobile.css must load after call.css")

    if SET_MODE_NEW not in js or SET_MODE_OLD in js:
        fail("Call validation failed: mobile scroll reset helper is missing")

    if not css_path.is_file():
        fail("Call validation failed: static/css/call-mobile.css is missing")
    if read_utf8(css_path) != CALL_MOBILE_CSS:
        fail("Call validation failed: call-mobile.css differs from the approved patch")

    # Guard the desktop contract: all station-specific CSS must remain inside media queries.
    if not CALL_MOBILE_CSS.lstrip().startswith("/*"):
        fail("Call validation failed: unexpected CSS header")
    if "@media (max-width: 768px)" not in CALL_MOBILE_CSS or "@media (max-width: 480px)" not in CALL_MOBILE_CSS:
        fail("Call validation failed: expected mobile breakpoints are missing")

    validate_json_and_python(project)


def validate_runtime(project: Path) -> None:
    sys.path.insert(0, str(project))
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
    except Exception as exc:
        fail(f"FastAPI import failed: {exc}")

    checks = {
        "/api/health": "status",
        "/": "FRAUD LAB",
        "/call": "call-mobile.css?v=1.0",
        "/sms": "FRAUD LAB",
        "/qr": "FRAUD LAB",
        "/static/css/call-mobile.css": "Call Station Mobile Overrides",
        "/static/js/call.js?v=8.6": "window.matchMedia('(max-width: 768px)').matches",
    }

    try:
        with TestClient(app) as client:
            for url, marker in checks.items():
                response = client.get(url)
                if response.status_code != 200:
                    fail(f"Runtime validation failed: {url} returned HTTP {response.status_code}")
                if marker not in response.text:
                    fail(f"Runtime validation failed: marker {marker!r} missing from {url}")

            health = client.get("/api/health").json()
            if health.get("status") != "ok":
                fail("Runtime validation failed: /api/health status is not ok")

            scenario_list = client.get("/api/scenarios")
            if scenario_list.status_code != 200:
                fail("Runtime validation failed: /api/scenarios did not return HTTP 200")
            listed = scenario_list.json()
            if not isinstance(listed, list) or not listed:
                fail("Runtime validation failed: /api/scenarios returned no scenarios")

            scenario_id = listed[0].get("scenario_id")
            if not scenario_id:
                fail("Runtime validation failed: first Call scenario has no scenario_id")
            scenario = client.get(f"/api/scenarios/{scenario_id}")
            if scenario.status_code != 200:
                fail(f"Runtime validation failed: scenario {scenario_id} did not load")
            payload = scenario.json()
            if not payload.get("start_node") or not payload.get("nodes"):
                fail(f"Runtime validation failed: scenario {scenario_id} is incomplete")
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"Runtime validation failed: {exc}")


def validate(project: Path) -> None:
    check_root(project)
    if detect_state(project) != "patched":
        fail("Patch is not in the expected applied state")
    validate_static(project)
    validate_runtime(project)
    print(
        "VALIDATION OK: Call mobile patch, UTF-8, JSON, Python import, "
        "FastAPI routes, Call scenario API and static assets"
    )


def restore_backup(project: Path, backup: Path, mark_rollback: bool = True) -> None:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        fail(f"Backup manifest missing: {backup}")
    manifest = json.loads(read_utf8(manifest_path))

    mapping = {
        "call_index.html": project / "frontend/call/index.html",
        "call.js": project / "static/js/call.js",
        "call-mobile.css": project / "static/css/call-mobile.css",
    }
    existed = manifest.get("files_existed", {})

    for backup_name, target in mapping.items():
        if existed.get(backup_name):
            source = backup / backup_name
            if not source.is_file():
                fail(f"Backup file missing: {source}")
            shutil.copy2(source, target)
        elif target.exists():
            target.unlink()

    if mark_rollback:
        manifest["rolled_back"] = True
        manifest["rolled_back_at"] = datetime.now().isoformat(timespec="seconds")
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"ROLLBACK OK: restored {backup}")


def apply_patch(project: Path) -> None:
    check_root(project)
    state = detect_state(project)

    if state == "patched":
        print("INFO: Call mobile patch is already applied; running validation only.")
        validate(project)
        return
    if state != "original":
        fail("Call files are not in the expected responsive-baseline state. No files were changed.")

    backup = create_backup(project, purpose="apply")
    html_path = project / "frontend/call/index.html"
    js_path = project / "static/js/call.js"
    css_path = project / "static/css/call-mobile.css"

    original_html = read_utf8(html_path)
    original_js = read_utf8(js_path)

    new_html = original_html.replace(
        CALL_CSS_LINK,
        CALL_CSS_LINK + "\n" + CALL_MOBILE_LINK,
        1,
    ).replace(CALL_SCRIPT_OLD, CALL_SCRIPT_NEW, 1)
    new_js = original_js.replace(SET_MODE_OLD, SET_MODE_NEW, 1)

    if new_html == original_html or new_js == original_js:
        fail("Patch anchors were not replaced as expected. No files were written.")

    try:
        html_path.write_text(new_html, encoding="utf-8")
        js_path.write_text(new_js, encoding="utf-8")
        css_path.write_text(CALL_MOBILE_CSS, encoding="utf-8")
        validate(project)
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(project, backup, mark_rollback=False)
        raise

    print(
        "APPLY OK: frontend/call/index.html updated; static/js/call.js updated; "
        "static/css/call-mobile.css created"
    )


def rollback_last(project: Path) -> None:
    check_root(project)
    base = backup_root(project)
    if not base.is_dir():
        fail(f"No Call mobile backups found at {base}")

    candidates: list[Path] = []
    for folder in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(read_utf8(manifest_path))
        except Exception:
            continue
        if manifest.get("purpose") == "apply" and not manifest.get("rolled_back", False):
            candidates.append(folder)

    if not candidates:
        fail("No unapplied Call mobile patch backup is available for rollback")

    restore_backup(project, candidates[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="FraudLab Call mobile responsive patch installer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup-only", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--validate", action="store_true")
    group.add_argument("--rollback-last", action="store_true")
    args = parser.parse_args()

    project = project_root()
    check_root(project)

    if args.backup_only:
        create_backup(project, purpose="manual")
    elif args.apply:
        apply_patch(project)
    elif args.validate:
        validate(project)
    elif args.rollback_last:
        rollback_last(project)


if __name__ == "__main__":
    main()
