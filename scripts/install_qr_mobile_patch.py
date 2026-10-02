from __future__ import annotations

import argparse
import compileall
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_NAME = "qr_mobile_v1"

QR_MOBILE_CSS = r'''/*
 FRAUD LAB — QR / Website Station Mobile Overrides
 Phase 1 · QR station only

 Loaded last. Rules are restricted to <= 768px and the qr-page scope so
 desktop/exhibition presentation and the other stations remain unchanged.
*/

@media (max-width: 768px) {
  html.qr-page,
  body.qr-page {
    width: 100%;
    min-height: 100%;
    overflow-x: hidden !important;
    overflow-y: auto !important;
  }

  body.qr-page {
    min-height: 100vh;
    min-height: 100dvh;
  }

  body.qr-page .qr-app {
    width: 100%;
    min-height: 100vh !important;
    min-height: 100dvh !important;
    height: auto !important;
    overflow: visible !important;
  }

  body.qr-page .qr-topbar {
    padding: max(16px, env(safe-area-inset-top)) max(14px, env(safe-area-inset-right)) 16px max(14px, env(safe-area-inset-left));
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 14px;
  }

  body.qr-page .station-name {
    overflow-wrap: anywhere;
  }

  body.qr-page .top-actions {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  body.qr-page .top-actions .secondary-btn {
    flex: 1 1 220px;
    min-width: 0;
    min-height: 52px !important;
    white-space: normal;
  }

  body.qr-page .qr-screen {
    width: calc(100% - 24px) !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 auto !important;
    padding: 20px 0 28px !important;
    overflow: visible !important;
    display: block !important;
  }

  body.qr-page #screen .intro-card,
  body.qr-page #screen .result-card,
  body.qr-page #screen .fatal-card,
  body.qr-page .qr-feedback-card {
    width: 100% !important;
    max-width: none !important;
    padding: 24px !important;
    margin: 0 auto !important;
  }

  body.qr-page #screen .intro-card h1,
  body.qr-page #screen .result-card h1,
  body.qr-page .qr-feedback-card h1 {
    max-width: none !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
  }

  body.qr-page .challenge-layout {
    width: 100%;
    height: auto !important;
    min-height: 0 !important;
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 20px !important;
    align-items: start !important;
  }

  body.qr-page .challenge-layout > * {
    min-width: 0;
    min-height: 0;
  }

  body.qr-page #screen .left-panel,
  body.qr-page #screen .browser-card,
  body.qr-page #screen .fake-site,
  body.qr-page #screen .poster-card {
    max-width: 100%;
  }

  body.qr-page #screen .left-panel {
    padding: 20px !important;
  }

  body.qr-page .progress {
    gap: 8px 14px;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  body.qr-page .progress span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  body.qr-page #screen .poster-card {
    margin-top: 16px !important;
    padding: 20px !important;
  }

  body.qr-page .qr-placeholder {
    max-width: 100%;
  }

  body.qr-page .scenario-qr-image {
    max-width: 100% !important;
    height: auto !important;
  }

  body.qr-page .choice-area {
    margin-top: 18px !important;
  }

  body.qr-page .choice-area h1,
  body.qr-page .qr-app .choice-area h1 {
    margin: 0 0 12px !important;
    font-size: clamp(1.6rem, 8vw, 2rem) !important;
    line-height: 1.15 !important;
    transform: none !important;
    transform-origin: initial !important;
  }

  body.qr-page .choice-grid {
    gap: 10px !important;
  }

  body.qr-page .choice-btn {
    width: 100%;
    height: auto !important;
    min-height: 60px !important;
    padding: 13px 15px !important;
    gap: 12px !important;
    align-items: flex-start !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
    word-break: normal;
  }

  body.qr-page .choice-btn span {
    flex: 0 0 32px;
    min-width: 32px;
    width: 32px !important;
    height: 32px !important;
  }

  body.qr-page .browser-card {
    order: -1;
    width: 100%;
    height: auto !important;
    max-height: none !important;
    overflow: hidden !important;
  }

  body.qr-page #screen .browser-card {
    padding: 18px !important;
  }

  body.qr-page .browser-top,
  body.qr-page #screen .fake-site {
    min-width: 0;
  }

  body.qr-page .address-bar {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  body.qr-page #screen .fake-site {
    padding: 20px !important;
  }

  body.qr-page .fake-form,
  body.qr-page .fake-input,
  body.qr-page .fake-input-control,
  body.qr-page .vehicle-lookup-result {
    max-width: 100%;
  }

  body.qr-page .vehicle-lookup-row {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 6px 12px;
  }

  body.qr-page .vehicle-lookup-row strong {
    max-width: 100%;
    text-align: left;
    overflow-wrap: anywhere;
  }

  body.qr-page .qr-feedback-card {
    overflow: visible !important;
  }

  body.qr-page .feedback-grid {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 16px !important;
  }

  body.qr-page .feedback-panel,
  body.qr-page .feedback-grid section {
    min-width: 0;
    padding: 20px;
  }

  body.qr-page .feedback-next {
    width: 100%;
    margin: 20px 0 0 !important;
  }

  body.qr-page .lesson-grid {
    grid-template-columns: minmax(0, 1fr) !important;
  }

  body.qr-page .result-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  body.qr-page .result-actions .primary-btn,
  body.qr-page .result-actions .secondary-btn {
    width: 100%;
    white-space: normal;
  }

  body.qr-page .safety-strip {
    margin-top: auto;
    min-height: 0;
    padding: 14px 12px max(14px, env(safe-area-inset-bottom));
    flex-wrap: wrap;
    gap: 8px 10px;
    text-align: center;
    font-size: clamp(.9rem, 4vw, 1rem);
  }

  body.qr-page .qr-timeout-modal {
    padding: 14px;
  }

  body.qr-page .qr-timeout-modal .timeout-card {
    width: 100%;
    max-height: calc(100vh - 28px);
    max-height: calc(100dvh - 28px);
    padding: 24px;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  body.qr-page .qr-timeout-modal .timeout-card h2 {
    font-size: clamp(1.55rem, 8vw, 2rem);
  }

  body.qr-page .qr-timeout-modal .timeout-card p {
    font-size: 1.05rem;
  }
}

@media (max-width: 480px) {
  body.qr-page .qr-topbar {
    padding: max(14px, env(safe-area-inset-top)) 12px 14px;
  }

  body.qr-page .top-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  body.qr-page .top-actions .secondary-btn {
    width: 100%;
  }

  body.qr-page .qr-screen {
    width: calc(100% - 20px) !important;
    padding-top: 14px !important;
  }

  body.qr-page #screen .intro-card,
  body.qr-page #screen .result-card,
  body.qr-page #screen .fatal-card,
  body.qr-page .qr-feedback-card {
    padding: 20px !important;
    border-radius: 20px;
  }

  body.qr-page #screen .left-panel,
  body.qr-page #screen .browser-card,
  body.qr-page #screen .fake-site,
  body.qr-page #screen .poster-card {
    padding: 16px !important;
  }

  body.qr-page .feedback-panel,
  body.qr-page .feedback-grid section {
    padding: 16px;
  }

  body.qr-page .safety-strip {
    font-size: .86rem;
  }
}
'''

EXPECTED_FILES = (
    "frontend/home/index.html",
    "static/css/mobile.css",
    "frontend/call/index.html",
    "static/css/call-mobile.css",
    "frontend/sms/index.html",
    "static/css/sms-mobile.css",
    "frontend/qr/index.html",
    "static/css/base.css",
    "static/css/qr.css",
    "static/css/fraud-dark.css",
    "static/css/fraud-premium-fixes.css",
    "static/js/qr.js",
    "backend/main.py",
    "data/qr_scenarios.json",
)

HOME_BASELINE_MARKER = '/static/css/mobile.css?v=1.0'
CALL_BASELINE_MARKER = '/static/css/call-mobile.css?v=1.0'
SMS_BASELINE_MARKER = '/static/css/sms-mobile.css?v=1.0'

HTML_OPEN_OLD = '<html lang="el">'
HTML_OPEN_NEW = '<html lang="el" class="qr-page">'
BODY_OPEN_OLD = '<body>'
BODY_OPEN_NEW = '<body class="qr-page">'
PREMIUM_LINK = '  <link rel="stylesheet" href="/static/css/fraud-premium-fixes.css?v=7.12">'
QR_MOBILE_LINK = '  <link rel="stylesheet" href="/static/css/qr-mobile.css?v=1.0">'
QR_SCRIPT_OLD = '<script src="/static/js/qr.js?v=9.0" defer></script>'
QR_SCRIPT_NEW = '<script src="/static/js/qr.js?v=9.1" defer></script>'

REGISTER_BLOCK_OLD = """  function registerActivity() {\n    resetIdleTimers();\n  }\n\n\n  function showIntro() {"""
REGISTER_BLOCK_NEW = """  function registerActivity() {\n    resetIdleTimers();\n  }\n\n\n  function resetMobileViewport() {\n    if (!window.matchMedia('(max-width: 768px)').matches) return;\n\n    window.requestAnimationFrame(() => {\n      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });\n      screen.scrollTop = 0;\n    });\n  }\n\n\n  function showIntro() {"""

RENDER_PATCHES = (
    (
        """    document.getElementById('startBtn').addEventListener('click', renderItem);\n    resetIdleTimers();""",
        """    document.getElementById('startBtn').addEventListener('click', renderItem);\n    resetMobileViewport();\n    resetIdleTimers();""",
    ),
    (
        """    setupFakeFormInteraction(fakeForm);\n    playMailNotification();\n    resetIdleTimers();""",
        """    setupFakeFormInteraction(fakeForm);\n    playMailNotification();\n    resetMobileViewport();\n    resetIdleTimers();""",
    ),
    (
        """    document.getElementById('nextBtn').addEventListener('click', () => {\n      if (currentIndex < data.items.length - 1) {\n        currentIndex += 1;\n        renderItem();\n      } else {\n        renderResult();\n      }\n    });\n\n    resetIdleTimers();""",
        """    document.getElementById('nextBtn').addEventListener('click', () => {\n      if (currentIndex < data.items.length - 1) {\n        currentIndex += 1;\n        renderItem();\n      } else {\n        renderResult();\n      }\n    });\n\n    resetMobileViewport();\n    resetIdleTimers();""",
    ),
    (
        """    document.getElementById('resultHomeBtn').addEventListener('click', () => {\n      window.location.href = '/';\n    });\n\n    resetIdleTimers();""",
        """    document.getElementById('resultHomeBtn').addEventListener('click', () => {\n      window.location.href = '/';\n    });\n\n    resetMobileViewport();\n    resetIdleTimers();""",
    ),
    (
        """      screen.innerHTML = `\n        <section class="fatal-card">\n          <h1>Το Station 3 χρειάζεται επανεκκίνηση</h1>\n          <button class="primary-btn" onclick="location.reload()">\n            ΕΠΑΝΕΚΚΙΝΗΣΗ\n          </button>\n        </section>\n      `;""",
        """      screen.innerHTML = `\n        <section class="fatal-card">\n          <h1>Το Station 3 χρειάζεται επανεκκίνηση</h1>\n          <button class="primary-btn" onclick="location.reload()">\n            ΕΠΑΝΕΚΚΙΝΗΣΗ\n          </button>\n        </section>\n      `;\n      resetMobileViewport();""",
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
    sms_text = read_utf8(project / "frontend/sms/index.html")
    if (
        HOME_BASELINE_MARKER not in home_text
        or CALL_BASELINE_MARKER not in call_text
        or SMS_BASELINE_MARKER not in sms_text
    ):
        fail(
            "Responsive Home/Call/SMS baseline markers are missing. "
            "Refusing to patch the stable/original repo."
        )


def backup_root(project: Path) -> Path:
    return project.parent / f"{project.name}_backups" / "qr_mobile"


def create_backup(project: Path, purpose: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(project) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    targets = {
        "qr_index.html": project / "frontend/qr/index.html",
        "qr.js": project / "static/js/qr.js",
        "qr-mobile.css": project / "static/css/qr-mobile.css",
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
    return all(new in js for _, new in RENDER_PATCHES)


def detect_state(project: Path) -> str:
    html = read_utf8(project / "frontend/qr/index.html")
    js = read_utf8(project / "static/js/qr.js")
    css_path = project / "static/css/qr-mobile.css"

    patched = (
        HTML_OPEN_NEW in html
        and BODY_OPEN_NEW in html
        and QR_MOBILE_LINK in html
        and QR_SCRIPT_NEW in html
        and HTML_OPEN_OLD not in html
        and QR_SCRIPT_OLD not in html
        and js_is_patched(js)
        and css_path.is_file()
        and read_utf8(css_path) == QR_MOBILE_CSS
    )
    if patched:
        return "patched"

    original = (
        HTML_OPEN_OLD in html
        and BODY_OPEN_OLD in html
        and QR_MOBILE_LINK not in html
        and QR_SCRIPT_OLD in html
        and QR_SCRIPT_NEW not in html
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
    html = read_utf8(project / "frontend/qr/index.html")
    js = read_utf8(project / "static/js/qr.js")
    css_path = project / "static/css/qr-mobile.css"

    if HTML_OPEN_NEW not in html or BODY_OPEN_NEW not in html:
        fail("QR validation failed: qr-page scope is missing")
    if QR_MOBILE_LINK not in html:
        fail("QR validation failed: qr-mobile.css link is missing")
    if QR_SCRIPT_NEW not in html or QR_SCRIPT_OLD in html:
        fail("QR validation failed: qr.js cache version is not v9.1")

    premium_pos = html.find(PREMIUM_LINK)
    mobile_pos = html.find(QR_MOBILE_LINK)
    if premium_pos < 0 or mobile_pos <= premium_pos:
        fail("QR validation failed: qr-mobile.css must load after premium CSS")

    if not js_is_patched(js):
        fail("QR validation failed: mobile viewport reset patch is incomplete")

    if not css_path.is_file():
        fail("QR validation failed: static/css/qr-mobile.css is missing")
    if read_utf8(css_path) != QR_MOBILE_CSS:
        fail("QR validation failed: qr-mobile.css differs from the approved patch")

    if "@media (max-width: 768px)" not in QR_MOBILE_CSS or "@media (max-width: 480px)" not in QR_MOBILE_CSS:
        fail("QR validation failed: expected mobile breakpoints are missing")
    if "body.qr-page .qr-app" not in QR_MOBILE_CSS or "body.qr-page .qr-screen" not in QR_MOBILE_CSS:
        fail("QR validation failed: QR-only scope is incomplete")

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
        "/sms": "FRAUD LAB",
        "/qr": "qr-mobile.css?v=1.0",
        "/static/css/qr-mobile.css": "QR / Website Station Mobile Overrides",
        "/static/js/qr.js?v=9.1": "resetMobileViewport",
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

            qr = client.get("/api/qr-challenge")
            if qr.status_code != 200:
                fail("Runtime validation failed: /api/qr-challenge did not return HTTP 200")
            payload = qr.json()
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                fail("Runtime validation failed: QR challenge returned no items")
            if not payload.get("educational_message") or not payload.get("max_score"):
                fail("Runtime validation failed: QR challenge payload is incomplete")
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
        "VALIDATION OK: QR mobile patch, UTF-8, JSON, Python import, "
        "FastAPI routes, QR challenge API and static assets"
    )


def restore_backup(project: Path, backup: Path, mark_rollback: bool = True) -> None:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        fail(f"Backup manifest missing: {backup}")
    manifest = json.loads(read_utf8(manifest_path))

    mapping = {
        "qr_index.html": project / "frontend/qr/index.html",
        "qr.js": project / "static/js/qr.js",
        "qr-mobile.css": project / "static/css/qr-mobile.css",
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
        print("INFO: QR mobile patch is already applied; running validation only.")
        validate(project)
        return
    if state != "original":
        fail("QR files are not in the expected responsive-baseline state. No files were changed.")

    backup = create_backup(project, purpose="apply")
    html_path = project / "frontend/qr/index.html"
    js_path = project / "static/js/qr.js"
    css_path = project / "static/css/qr-mobile.css"

    original_html = read_utf8(html_path)
    original_js = read_utf8(js_path)

    new_html = original_html
    new_html = replace_once(new_html, HTML_OPEN_OLD, HTML_OPEN_NEW, "html scope")
    new_html = replace_once(new_html, BODY_OPEN_OLD, BODY_OPEN_NEW, "body scope")
    new_html = replace_once(
        new_html,
        PREMIUM_LINK,
        PREMIUM_LINK + "\n" + QR_MOBILE_LINK,
        "mobile css link",
    )
    new_html = replace_once(new_html, QR_SCRIPT_OLD, QR_SCRIPT_NEW, "qr script version")

    new_js = replace_once(original_js, REGISTER_BLOCK_OLD, REGISTER_BLOCK_NEW, "viewport reset helper")
    for index, (old, new) in enumerate(RENDER_PATCHES, start=1):
        new_js = replace_once(new_js, old, new, f"render viewport reset {index}")

    try:
        html_path.write_text(new_html, encoding="utf-8")
        js_path.write_text(new_js, encoding="utf-8")
        css_path.write_text(QR_MOBILE_CSS, encoding="utf-8")
        validate(project)
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(project, backup, mark_rollback=False)
        raise

    print(
        "APPLY OK: frontend/qr/index.html updated; static/js/qr.js updated; "
        "static/css/qr-mobile.css created"
    )


def rollback_last(project: Path) -> None:
    check_root(project)
    base = backup_root(project)
    if not base.is_dir():
        fail(f"No QR mobile backups found at {base}")

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
        fail("No unapplied QR mobile patch backup is available for rollback")

    restore_backup(project, candidates[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="FraudLab QR mobile responsive patch installer")
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
