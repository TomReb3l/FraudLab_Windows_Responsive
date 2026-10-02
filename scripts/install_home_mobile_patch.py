from __future__ import annotations

import argparse
import compileall
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_NAME = "home_mobile_v1"

MOBILE_CSS = r'''/*
 FRAUD LAB — Mobile Responsive Overrides
 Home only · Phase 1

 Loaded after exhibition-tv.css so mobile browsers can scroll normally
 while the desktop/exhibition layout remains unchanged.
*/

@media (max-width: 768px) {
  html.home-page,
  body.home-page {
    width: 100%;
    height: auto;
    min-height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
  }

  body.home-page {
    min-height: 100vh;
    min-height: 100dvh;
  }

  body.home-page .home-shell {
    width: min(100% - 24px, 1400px);
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    margin: 0 auto;
    padding: max(28px, env(safe-area-inset-top)) 0 max(28px, env(safe-area-inset-bottom));
    display: block;
    overflow: visible;
  }

  body.home-page .hero {
    max-width: 100%;
    margin-bottom: 28px;
  }

  body.home-page .hero h1 {
    font-size: clamp(2.35rem, 11vw, 4.2rem);
    line-height: 1;
    overflow-wrap: anywhere;
  }

  body.home-page .hero-copy {
    display: block !important;
    max-width: 100%;
    margin: 20px 0;
    font-size: clamp(1rem, 3.8vw, 1.2rem);
    line-height: 1.55;
  }

  body.home-page .safety-message {
    display: flex !important;
    width: 100%;
    max-width: 100%;
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 14px;
    font-size: .82rem;
    line-height: 1.25;
    text-align: center;
  }

  body.home-page .stations {
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: none;
    gap: 16px;
  }

  body.home-page .station-card,
  body.home-page .station-card.featured {
    grid-column: auto;
    width: 100%;
    height: auto;
    min-height: 0;
    padding: 22px;
    align-items: flex-start;
  }

  body.home-page .station-card.featured {
    text-align: center;
  }

  body.home-page .station-content {
    min-width: 0;
  }

  body.home-page .station-card h2 {
    margin: 10px 0;
    font-size: clamp(1.55rem, 6vw, 2.15rem);
    overflow-wrap: anywhere;
  }

  body.home-page .station-card p {
    margin: 8px 0 0;
    max-width: 100%;
    font-size: 1rem;
    line-height: 1.5;
  }

  body.home-page .station-footer,
  body.home-page .station-card.featured .station-footer {
    display: flex !important;
    width: 100%;
    margin-top: 20px;
    padding-top: 14px;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  body.home-page .home-footer {
    display: block !important;
    margin-top: 24px;
    padding: 18px 2px;
  }

  body.home-page .home-footer p {
    margin: 0;
    line-height: 1.5;
  }
}

@media (max-width: 480px) {
  body.home-page .home-shell {
    width: calc(100% - 20px);
    padding-top: max(22px, env(safe-area-inset-top));
  }

  body.home-page .brand-kicker {
    margin-bottom: 10px;
    font-size: .82rem;
  }

  body.home-page .hero h1 {
    font-size: clamp(2.15rem, 11.5vw, 3.2rem);
    letter-spacing: -.035em;
  }

  body.home-page .hero-copy {
    margin: 16px 0;
  }

  body.home-page .station-number {
    display: none;
  }

  body.home-page .station-card,
  body.home-page .station-card.featured {
    padding: 20px;
  }

  body.home-page .station-footer,
  body.home-page .station-card.featured .station-footer {
    font-size: .9rem;
  }
}
'''

EXPECTED = {
    "frontend/home/index.html": "home HTML",
    "static/css/base.css": "base CSS",
    "static/css/home.css": "home CSS",
    "static/css/exhibition-tv.css": "exhibition CSS",
    "backend/main.py": "FastAPI app",
    "frontend/call/index.html": "Call frontend",
    "frontend/sms/index.html": "SMS frontend",
    "frontend/qr/index.html": "QR frontend",
}

HTML_ANCHORS = {
    "html": '<html lang="el">',
    "body": '<body>',
    "tv_css": '  <link rel="stylesheet" href="/static/css/exhibition-tv.css">',
}
PATCHED_HTML_MARKERS = {
    "html": '<html lang="el" class="home-page">',
    "body": '<body class="home-page">',
    "mobile_css": '  <link rel="stylesheet" href="/static/css/mobile.css?v=1.0">',
}


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(code)


def root() -> Path:
    return Path.cwd().resolve()


def check_root(project: Path) -> None:
    missing = [rel for rel in EXPECTED if not (project / rel).is_file()]
    if missing:
        fail(
            "This does not look like the FraudLab_Windows project root. Missing: "
            + ", ".join(missing)
        )


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"UTF-8 decode failed for {path}: {exc}")


def backup_root(project: Path) -> Path:
    return project.parent / f"{project.name}_backups" / "home_mobile"


def create_backup(project: Path, purpose: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(project) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    home = project / "frontend/home/index.html"
    mobile = project / "static/css/mobile.css"

    shutil.copy2(home, dest / "home_index.html")
    mobile_existed = mobile.exists()
    if mobile_existed:
        shutil.copy2(mobile, dest / "mobile.css")

    manifest = {
        "patch": PATCH_NAME,
        "purpose": purpose,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "mobile_css_existed": mobile_existed,
        "rolled_back": False,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"BACKUP: {dest}")
    return dest


def detect_state(project: Path) -> str:
    home_text = read_utf8(project / "frontend/home/index.html")
    patched = all(marker in home_text for marker in PATCHED_HTML_MARKERS.values())
    original = all(anchor in home_text for anchor in HTML_ANCHORS.values())
    mobile = project / "static/css/mobile.css"

    if patched and mobile.is_file() and read_utf8(mobile) == MOBILE_CSS:
        return "patched"
    if original and PATCHED_HTML_MARKERS["mobile_css"] not in home_text:
        return "original"
    return "unexpected"


def validate_static(project: Path) -> None:
    home = project / "frontend/home/index.html"
    css = project / "static/css/mobile.css"
    home_text = read_utf8(home)

    for name, marker in PATCHED_HTML_MARKERS.items():
        if marker not in home_text:
            fail(f"Home validation failed: missing {name} marker")

    if not css.is_file():
        fail("Home validation failed: static/css/mobile.css is missing")
    if read_utf8(css) != MOBILE_CSS:
        fail("Home validation failed: static/css/mobile.css differs from the approved patch")

    tv_pos = home_text.find('/static/css/exhibition-tv.css')
    mobile_pos = home_text.find('/static/css/mobile.css?v=1.0')
    if tv_pos < 0 or mobile_pos < 0 or mobile_pos <= tv_pos:
        fail("Home validation failed: mobile.css must load after exhibition-tv.css")

    if '<script' in home_text.lower():
        fail("Unexpected script tag detected in Home; patch expected a static Home page")

    # UTF-8 and JSON integrity across project data.
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
        "/qr": "FRAUD LAB",
        "/static/css/mobile.css": "Mobile Responsive Overrides",
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

            for url in ("/api/scenarios", "/api/sms-challenge", "/api/qr-challenge"):
                response = client.get(url)
                if response.status_code != 200:
                    fail(f"Runtime validation failed: {url} returned HTTP {response.status_code}")
                response.json()
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
    print("VALIDATION OK: Home mobile patch, UTF-8, JSON, Python import, FastAPI routes and APIs")


def apply_patch(project: Path) -> None:
    check_root(project)
    state = detect_state(project)
    if state == "patched":
        print("INFO: Home mobile patch is already applied; running validation only.")
        validate(project)
        return
    if state != "original":
        fail("Home files are not in the expected source state. No files were changed.")

    backup = create_backup(project, purpose="apply")
    home_path = project / "frontend/home/index.html"
    css_path = project / "static/css/mobile.css"

    original_home = read_utf8(home_path)
    new_home = original_home
    new_home = new_home.replace(HTML_ANCHORS["html"], PATCHED_HTML_MARKERS["html"], 1)
    new_home = new_home.replace(HTML_ANCHORS["body"], PATCHED_HTML_MARKERS["body"], 1)
    new_home = new_home.replace(
        HTML_ANCHORS["tv_css"],
        HTML_ANCHORS["tv_css"] + "\n" + PATCHED_HTML_MARKERS["mobile_css"],
        1,
    )

    try:
        home_path.write_text(new_home, encoding="utf-8")
        css_path.write_text(MOBILE_CSS, encoding="utf-8")
        validate(project)
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(project, backup, mark_rollback=False)
        raise

    print("APPLY OK: frontend/home/index.html updated; static/css/mobile.css created")


def restore_backup(project: Path, backup: Path, mark_rollback: bool = True) -> None:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        fail(f"Backup manifest missing: {backup}")
    manifest = json.loads(read_utf8(manifest_path))

    home_backup = backup / "home_index.html"
    if not home_backup.is_file():
        fail(f"Backup Home file missing: {home_backup}")

    shutil.copy2(home_backup, project / "frontend/home/index.html")
    mobile_target = project / "static/css/mobile.css"
    if manifest.get("mobile_css_existed"):
        mobile_backup = backup / "mobile.css"
        if not mobile_backup.is_file():
            fail(f"Backup mobile.css missing: {mobile_backup}")
        shutil.copy2(mobile_backup, mobile_target)
    elif mobile_target.exists():
        mobile_target.unlink()

    if mark_rollback:
        manifest["rolled_back"] = True
        manifest["rolled_back_at"] = datetime.now().isoformat(timespec="seconds")
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"ROLLBACK OK: restored {backup}")


def rollback_last(project: Path) -> None:
    check_root(project)
    base = backup_root(project)
    if not base.is_dir():
        fail(f"No Home mobile backups found at {base}")

    candidates = []
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
        fail("No unapplied Home mobile patch backup is available for rollback")

    restore_backup(project, candidates[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="FraudLab Home mobile responsive patch installer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup-only", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--validate", action="store_true")
    group.add_argument("--rollback-last", action="store_true")
    args = parser.parse_args()

    project = root()
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
