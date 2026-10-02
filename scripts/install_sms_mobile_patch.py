from __future__ import annotations

import argparse
import compileall
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_NAME = "sms_mobile_v1"

SMS_MOBILE_CSS = r'''/*
 FRAUD LAB — SMS / Phishing Station Mobile Overrides
 Phase 1 · SMS station only

 Loaded last. Rules are restricted to <= 768px and the sms-page scope so
 desktop/exhibition presentation and the other stations remain unchanged.
*/

@media (max-width: 768px) {
  html.sms-page,
  body.sms-page {
    height: auto;
    min-height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
  }

  body.sms-page {
    min-height: 100vh;
    min-height: 100dvh;
  }

  body.sms-page .sms-app {
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    overflow: visible;
  }

  body.sms-page .sms-screen {
    flex: 1 0 auto;
    width: calc(100% - 20px);
    max-width: 100%;
    min-height: 0;
    margin: 0 auto;
    padding: 20px 0 24px;
    overflow: visible;
    display: block;
  }

  body.sms-page .intro-card,
  body.sms-page .feedback-view,
  body.sms-page .premium-view,
  body.sms-page .feedback-shell,
  body.sms-page .result-card,
  body.sms-page .fatal-card {
    height: auto;
    min-height: 0;
  }

  body.sms-page .intro-card,
  body.sms-page .result-card,
  body.sms-page .fatal-card {
    padding: 24px 20px;
    overflow: visible;
  }

  body.sms-page .intro-card h1,
  body.sms-page .result-card h1 {
    font-size: clamp(2rem, 8.4vw, 3rem);
    line-height: 1.08;
    overflow-wrap: anywhere;
  }

  body.sms-page .intro-card p,
  body.sms-page .result-copy {
    font-size: 1rem;
    line-height: 1.5;
  }

  body.sms-page .intro-card .primary-btn {
    width: 100%;
    min-width: 0;
  }

  body.sms-page .challenge-layout {
    width: 100%;
    min-width: 0;
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
  }

  body.sms-page .challenge-info {
    min-width: 0;
    padding: 0;
  }

  body.sms-page .phone-preview {
    order: -1;
    width: 100%;
    min-width: 0;
  }

  body.sms-page .phone-device {
    width: min(360px, 100%);
    min-height: 0;
    padding: 10px;
    border-width: 4px;
    border-radius: 34px;
  }

  body.sms-page .message-area {
    min-height: 260px;
    padding: 22px 10px;
  }

  body.sms-page .sms-bubble {
    width: 94%;
    padding: 14px;
    overflow-wrap: anywhere;
  }

  body.sms-page .progress-row {
    flex-wrap: wrap;
    gap: 8px 14px;
    padding-bottom: 14px;
    font-size: .78rem;
    letter-spacing: .05em;
  }

  body.sms-page .category {
    margin-top: 20px;
  }

  body.sms-page .challenge-info h1 {
    font-size: clamp(2rem, 8vw, 2.8rem);
  }

  body.sms-page .question-copy {
    font-size: 1rem;
  }

  body.sms-page .choice-grid {
    margin-top: 20px;
    gap: 12px;
  }

  body.sms-page .choice-btn {
    min-width: 0;
    min-height: 58px;
    gap: 12px;
    padding: 15px 16px;
    overflow-wrap: anywhere;
  }

  body.sms-page .choice-number {
    flex-basis: 36px;
    height: 36px;
  }

  body.sms-page .feedback-view,
  body.sms-page .premium-view {
    display: block;
    overflow: visible;
  }

  body.sms-page .feedback-shell {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px;
    overflow: visible;
  }

  body.sms-page .premium-headline-row,
  body.sms-page .feedback-summary-top {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  body.sms-page .section-title-small {
    font-size: clamp(1.2rem, 6vw, 1.7rem);
  }

  body.sms-page .feedback-summary-card,
  body.sms-page .detail-card {
    min-width: 0;
    padding: 18px;
  }

  body.sms-page .score-chip {
    max-width: 100%;
    flex-wrap: wrap;
    gap: 6px 8px;
    padding: 10px 12px;
    white-space: normal;
    line-height: 1.3;
  }

  body.sms-page .feedback-result {
    max-width: 100%;
    white-space: normal;
    line-height: 1.3;
  }

  body.sms-page .feedback-card-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }

  body.sms-page .feedback-flags-list {
    padding-left: 20px;
  }

  body.sms-page .feedback-actions-row {
    justify-content: stretch;
  }

  body.sms-page .feedback-actions-row .primary-btn {
    width: 100%;
    min-width: 0;
    min-height: 58px;
  }

  body.sms-page .sms-final-card {
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow: visible;
  }

  body.sms-page .sms-final-card .victim-alert {
    width: 100%;
    max-width: 100%;
    padding: 12px 14px;
    margin: 0;
    font-size: 1rem;
    line-height: 1.3;
  }

  body.sms-page .sms-final-card h1 {
    white-space: normal;
    overflow-wrap: anywhere;
  }

  body.sms-page .lesson-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
    margin-top: 0;
  }

  body.sms-page .sms-final-card .lesson-grid section {
    min-height: 0;
    padding: 16px;
  }

  body.sms-page .result-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  body.sms-page .result-actions .primary-btn,
  body.sms-page .result-actions .secondary-btn {
    width: 100%;
    min-width: 0;
    min-height: 56px;
  }

  body.sms-page .safety-strip {
    min-height: 0;
    padding: 12px 10px max(12px, env(safe-area-inset-bottom));
    flex-wrap: wrap;
    gap: 6px 8px;
    font-size: .76rem;
    line-height: 1.25;
    text-align: center;
  }

  body.sms-page .timeout-modal {
    padding: 14px;
  }

  body.sms-page .timeout-card {
    padding: 22px 18px;
  }

  body.sms-page .timeout-card h2 {
    font-size: clamp(1.45rem, 7vw, 2rem);
    line-height: 1.1;
  }

  body.sms-page .timeout-card p {
    font-size: 1rem;
  }

  body.sms-page .timeout-card .primary-btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  body.sms-page .sms-topbar {
    min-height: 0;
    gap: 12px;
    padding: max(14px, env(safe-area-inset-top)) 14px 14px;
  }

  body.sms-page .station-name {
    font-size: .92rem;
    line-height: 1.3;
  }

  body.sms-page .top-actions {
    gap: 8px;
  }

  body.sms-page .secondary-btn {
    min-height: 48px;
    white-space: normal;
  }

  body.sms-page .sms-screen {
    width: calc(100% - 16px);
    padding-top: 16px;
  }

  body.sms-page .intro-card,
  body.sms-page .result-card,
  body.sms-page .fatal-card,
  body.sms-page .feedback-shell {
    padding-left: 18px;
    padding-right: 18px;
  }

  body.sms-page .phone-device {
    width: 100%;
    border-radius: 30px;
  }

  body.sms-page .message-area {
    min-height: 240px;
    padding-top: 18px;
    padding-bottom: 18px;
  }

  body.sms-page .feedback-summary-card,
  body.sms-page .detail-card {
    padding: 16px;
  }
}
'''

EXPECTED_FILES = (
    "frontend/home/index.html",
    "static/css/mobile.css",
    "frontend/call/index.html",
    "static/css/call-mobile.css",
    "frontend/sms/index.html",
    "static/css/base.css",
    "static/css/sms.css",
    "static/css/fraud-dark.css",
    "static/css/fraud-premium-fixes.css",
    "static/js/sms.js",
    "backend/main.py",
    "data/sms_scenarios.json",
    "frontend/qr/index.html",
)

HOME_BASELINE_MARKER = '/static/css/mobile.css?v=1.0'
CALL_BASELINE_MARKER = '/static/css/call-mobile.css?v=1.0'

HTML_OPEN_OLD = '<html lang="el">'
HTML_OPEN_NEW = '<html lang="el" class="sms-page">'
BODY_OPEN_OLD = '<body>'
BODY_OPEN_NEW = '<body class="sms-page">'
PREMIUM_LINK = '  <link rel="stylesheet" href="/static/css/fraud-premium-fixes.css?v=7.12">'
SMS_MOBILE_LINK = '  <link rel="stylesheet" href="/static/css/sms-mobile.css?v=1.0">'
SMS_SCRIPT_OLD = '<script src="/static/js/sms.js?v=7.11" defer></script>'
SMS_SCRIPT_NEW = '<script src="/static/js/sms.js?v=7.12" defer></script>'

REGISTER_BLOCK_OLD = """  function registerActivity() {\n    resetIdleTimers();\n  }\n\n\n  function scoreLabel(value) {"""
REGISTER_BLOCK_NEW = """  function registerActivity() {\n    resetIdleTimers();\n  }\n\n\n  function resetMobileScroll() {\n    if (window.matchMedia('(max-width: 768px)').matches) {\n      window.scrollTo(0, 0);\n    }\n  }\n\n\n  function scoreLabel(value) {"""

RENDER_PATCHES = (
    (
        """    `;\n\n    document\n      .getElementById('startBtn')""",
        """    `;\n\n    resetMobileScroll();\n\n    document\n      .getElementById('startBtn')""",
    ),
    (
        """    `;\n\n\n    document\n      .querySelectorAll('[data-choice-index]')""",
        """    `;\n\n    resetMobileScroll();\n\n    document\n      .querySelectorAll('[data-choice-index]')""",
    ),
    (
        """    `;\n\n    document\n      .getElementById('nextBtn')""",
        """    `;\n\n    resetMobileScroll();\n\n    document\n      .getElementById('nextBtn')""",
    ),
    (
        """    `;\n\n\n    document\n      .getElementById('retryBtn')""",
        """    `;\n\n    resetMobileScroll();\n\n    document\n      .getElementById('retryBtn')""",
    ),
    (
        """    `;\n  }\n\n\n  async function init()""",
        """    `;\n\n    resetMobileScroll();\n  }\n\n\n  async function init()""",
    ),
)


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
    call_text = read_utf8(project / "frontend/call/index.html")
    if HOME_BASELINE_MARKER not in home_text or CALL_BASELINE_MARKER not in call_text:
        fail(
            "Responsive Home/Call baseline markers are missing. "
            "Refusing to patch the stable/original repo."
        )


def backup_root(project: Path) -> Path:
    return project.parent / f"{project.name}_backups" / "sms_mobile"


def create_backup(project: Path, purpose: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(project) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    targets = {
        "sms_index.html": project / "frontend/sms/index.html",
        "sms.js": project / "static/js/sms.js",
        "sms-mobile.css": project / "static/css/sms-mobile.css",
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


def js_is_original(js: str) -> bool:
    if REGISTER_BLOCK_OLD not in js or REGISTER_BLOCK_NEW in js:
        return False
    return all(old in js and new not in js for old, new in RENDER_PATCHES)


def js_is_patched(js: str) -> bool:
    if REGISTER_BLOCK_NEW not in js or REGISTER_BLOCK_OLD in js:
        return False
    return all(new in js and old not in js for old, new in RENDER_PATCHES)


def detect_state(project: Path) -> str:
    html = read_utf8(project / "frontend/sms/index.html")
    js = read_utf8(project / "static/js/sms.js")
    css_path = project / "static/css/sms-mobile.css"

    patched = (
        HTML_OPEN_NEW in html
        and BODY_OPEN_NEW in html
        and SMS_MOBILE_LINK in html
        and SMS_SCRIPT_NEW in html
        and HTML_OPEN_OLD not in html
        and SMS_SCRIPT_OLD not in html
        and js_is_patched(js)
        and css_path.is_file()
        and read_utf8(css_path) == SMS_MOBILE_CSS
    )
    if patched:
        return "patched"

    original = (
        HTML_OPEN_OLD in html
        and BODY_OPEN_OLD in html
        and SMS_MOBILE_LINK not in html
        and SMS_SCRIPT_OLD in html
        and SMS_SCRIPT_NEW not in html
        and js_is_original(js)
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
    html = read_utf8(project / "frontend/sms/index.html")
    js = read_utf8(project / "static/js/sms.js")
    css_path = project / "static/css/sms-mobile.css"

    if HTML_OPEN_NEW not in html or BODY_OPEN_NEW not in html:
        fail("SMS validation failed: sms-page scope is missing")
    if SMS_MOBILE_LINK not in html:
        fail("SMS validation failed: sms-mobile.css link is missing")
    if SMS_SCRIPT_NEW not in html or SMS_SCRIPT_OLD in html:
        fail("SMS validation failed: sms.js cache version is not v7.12")

    premium_pos = html.find(PREMIUM_LINK)
    mobile_pos = html.find(SMS_MOBILE_LINK)
    if premium_pos < 0 or mobile_pos <= premium_pos:
        fail("SMS validation failed: sms-mobile.css must load after premium CSS")

    if not js_is_patched(js):
        fail("SMS validation failed: mobile scroll reset patch is incomplete")

    if not css_path.is_file():
        fail("SMS validation failed: static/css/sms-mobile.css is missing")
    if read_utf8(css_path) != SMS_MOBILE_CSS:
        fail("SMS validation failed: sms-mobile.css differs from the approved patch")

    if "@media (max-width: 768px)" not in SMS_MOBILE_CSS or "@media (max-width: 480px)" not in SMS_MOBILE_CSS:
        fail("SMS validation failed: expected mobile breakpoints are missing")

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
        "/call": "FRAUD LAB",
        "/sms": "sms-mobile.css?v=1.0",
        "/qr": "FRAUD LAB",
        "/static/css/sms-mobile.css": "SMS / Phishing Station Mobile Overrides",
        "/static/js/sms.js?v=7.12": "resetMobileScroll",
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

            sms = client.get("/api/sms-challenge")
            if sms.status_code != 200:
                fail("Runtime validation failed: /api/sms-challenge did not return HTTP 200")
            payload = sms.json()
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                fail("Runtime validation failed: SMS challenge returned no items")
            if not payload.get("educational_message") or not payload.get("max_score"):
                fail("Runtime validation failed: SMS challenge payload is incomplete")
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
        "VALIDATION OK: SMS mobile patch, UTF-8, JSON, Python import, "
        "FastAPI routes, SMS challenge API and static assets"
    )


def restore_backup(project: Path, backup: Path, mark_rollback: bool = True) -> None:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        fail(f"Backup manifest missing: {backup}")
    manifest = json.loads(read_utf8(manifest_path))

    mapping = {
        "sms_index.html": project / "frontend/sms/index.html",
        "sms.js": project / "static/js/sms.js",
        "sms-mobile.css": project / "static/css/sms-mobile.css",
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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"Patch anchor {label!r} expected once, found {count}")
    return text.replace(old, new, 1)


def apply_patch(project: Path) -> None:
    check_root(project)
    state = detect_state(project)

    if state == "patched":
        print("INFO: SMS mobile patch is already applied; running validation only.")
        validate(project)
        return
    if state != "original":
        fail("SMS files are not in the expected responsive-baseline state. No files were changed.")

    backup = create_backup(project, purpose="apply")
    html_path = project / "frontend/sms/index.html"
    js_path = project / "static/js/sms.js"
    css_path = project / "static/css/sms-mobile.css"

    original_html = read_utf8(html_path)
    original_js = read_utf8(js_path)

    new_html = original_html
    new_html = replace_once(new_html, HTML_OPEN_OLD, HTML_OPEN_NEW, "html scope")
    new_html = replace_once(new_html, BODY_OPEN_OLD, BODY_OPEN_NEW, "body scope")
    new_html = replace_once(
        new_html,
        PREMIUM_LINK,
        PREMIUM_LINK + "\n" + SMS_MOBILE_LINK,
        "mobile css link",
    )
    new_html = replace_once(new_html, SMS_SCRIPT_OLD, SMS_SCRIPT_NEW, "sms script version")

    new_js = replace_once(original_js, REGISTER_BLOCK_OLD, REGISTER_BLOCK_NEW, "scroll helper")
    for index, (old, new) in enumerate(RENDER_PATCHES, start=1):
        new_js = replace_once(new_js, old, new, f"render scroll reset {index}")

    try:
        html_path.write_text(new_html, encoding="utf-8")
        js_path.write_text(new_js, encoding="utf-8")
        css_path.write_text(SMS_MOBILE_CSS, encoding="utf-8")
        validate(project)
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(project, backup, mark_rollback=False)
        raise

    print(
        "APPLY OK: frontend/sms/index.html updated; static/js/sms.js updated; "
        "static/css/sms-mobile.css created"
    )


def rollback_last(project: Path) -> None:
    check_root(project)
    base = backup_root(project)
    if not base.is_dir():
        fail(f"No SMS mobile backups found at {base}")

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
        fail("No unapplied SMS mobile patch backup is available for rollback")

    restore_backup(project, candidates[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="FraudLab SMS mobile responsive patch installer")
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
