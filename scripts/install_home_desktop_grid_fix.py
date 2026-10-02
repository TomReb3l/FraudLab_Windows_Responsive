#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FraudLab Responsive - Home desktop exhibition grid safety patch.

Purpose:
- Fix the featured Call card overlapping the SMS/QR row on shorter desktop
  exhibition viewports such as 1440x900 and 1366x768.
- Preserve the validated phone/tablet responsive behaviour.
- Preserve 1920x1080 exhibition appearance.

Changes only:
  static/css/mobile.css

Usage:
  python scripts/install_home_desktop_grid_fix.py --backup-only
  python scripts/install_home_desktop_grid_fix.py --apply
  python scripts/install_home_desktop_grid_fix.py --validate
  python scripts/install_home_desktop_grid_fix.py --rollback-last
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

TARGET = Path("static/css/mobile.css")

LANDSCAPE_TABLET_MARKER = (
    "@media (max-width: 768px), "
    "(orientation: landscape) and (max-width: 1024px) and (max-height: 600px), "
    "(min-width: 769px) and (max-width: 1024px) and (any-pointer: coarse), "
    "(orientation: landscape) and (min-width: 1025px) and (max-width: 1366px) "
    "and (max-height: 1024px) and (any-pointer: coarse) {"
)

FIX_BLOCK = """

/* HOME DESKTOP EXHIBITION GRID SAFETY
   The featured card must respect the grid row height on shorter desktop
   viewports instead of forcing the original 260px minimum into row 2. */
@media (min-width: 769px) and (max-height: 950px) {
  body.home-page .station-card.featured {
    min-height: 0;
  }
}
"""

FIX_MARKER = "HOME DESKTOP EXHIBITION GRID SAFETY"


def die(message: str) -> NoReturn:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def project_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    required = [
        root / "backend/main.py",
        root / "frontend/home/index.html",
        root / "frontend/call/index.html",
        root / "frontend/sms/index.html",
        root / "frontend/qr/index.html",
        root / "static/css/home.css",
        root / "static/css/exhibition-tv.css",
        root / TARGET,
        root / "static/css/call-mobile.css",
        root / "static/css/sms-mobile.css",
        root / "static/css/qr-mobile.css",
    ]
    missing = [p.relative_to(root) for p in required if not p.is_file()]
    if missing:
        die(
            "Expected FraudLab_Windows_Responsive files are missing: "
            + ", ".join(str(p) for p in missing)
        )
    return root


def backup_root(root: Path) -> Path:
    return root.parent / f"{root.name}_backups" / "home_desktop_grid"


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        die(f"UTF-8 decode failed for {path}: {exc}")


def inspect_state(root: Path) -> str:
    css = read_utf8(root / TARGET)
    if "body.home-page" not in css:
        die(f"Unexpected {TARGET}: Home scope marker not found")
    if LANDSCAPE_TABLET_MARKER not in css:
        die(
            "Expected landscape/tablet responsive baseline is not present in "
            f"{TARGET}. Apply/validate install_landscape_tablet_patch.py first."
        )

    count = css.count(FIX_MARKER)
    if count == 0:
        return "original"
    if count == 1 and css.count(FIX_BLOCK.strip()) == 1:
        return "patched"
    die(f"Unexpected or partially applied Home desktop grid patch in {TARGET}")


def create_backup(root: Path) -> Path:
    state = inspect_state(root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(root) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    target = dest / TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / TARGET, target)

    manifest = {
        "created": stamp,
        "state": state,
        "files": [TARGET.as_posix()],
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"BACKUP: {dest}")
    return dest


def validate_json(root: Path) -> None:
    for path in root.rglob("*.json"):
        if any(part in {".git", ".venv"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            die(f"UTF-8 decode failed: {path.relative_to(root)}: {exc}")
        if "????" in text:
            die(f"Possible encoding corruption detected in {path.relative_to(root)}")
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            die(f"JSON validation failed: {path.relative_to(root)}: {exc}")


def validate_runtime(root: Path) -> None:
    sys.path.insert(0, str(root))
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
    except Exception as exc:
        die(f"FastAPI import failed: {exc}")

    try:
        client = TestClient(app)
        for route in ("/", "/call", "/sms", "/qr", "/api/health"):
            response = client.get(route)
            if response.status_code != 200:
                die(f"Route validation failed: {route} -> HTTP {response.status_code}")

        response = client.get("/static/css/mobile.css")
        if response.status_code != 200:
            die(
                "Static CSS validation failed: /static/css/mobile.css -> "
                f"HTTP {response.status_code}"
            )
        if FIX_MARKER not in response.text:
            die("Home desktop grid fix is not being served from /static/css/mobile.css")
    except SystemExit:
        raise
    except Exception as exc:
        die(f"Runtime validation failed: {exc}")


def validate(root: Path) -> None:
    if inspect_state(root) != "patched":
        die("Home desktop grid fix is not in the expected applied state")

    css = read_utf8(root / TARGET)
    if css.count(FIX_MARKER) != 1:
        die("Expected exactly one Home desktop grid fix marker")
    if "@media (min-width: 769px) and (max-height: 950px)" not in css:
        die("Expected short-desktop media query is missing")
    if "body.home-page .station-card.featured" not in css:
        die("Expected featured Home card selector is missing")
    if "min-height: 0;" not in css:
        die("Expected featured-card min-height reset is missing")

    validate_json(root)
    validate_runtime(root)
    print(
        "VALIDATION OK: Home desktop grid safety fix, responsive baseline, UTF-8, "
        "JSON, FastAPI routes and CSS asset"
    )


def restore_backup(root: Path, backup: Path) -> None:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        die(f"Backup manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel_text in manifest.get("files", []):
        rel = Path(rel_text)
        source = backup / rel
        if not source.is_file():
            die(f"Backup file missing: {source}")
        shutil.copy2(source, root / rel)
    print(f"ROLLBACK OK: restored {backup}")


def latest_backup(root: Path) -> Path:
    base = backup_root(root)
    if not base.is_dir():
        die("No home_desktop_grid backup directory exists")
    backups = sorted(p for p in base.iterdir() if p.is_dir())
    if not backups:
        die("No home_desktop_grid backups found")
    return backups[-1]


def apply_patch(root: Path) -> None:
    state = inspect_state(root)
    if state == "patched":
        print("INFO: Home desktop grid fix is already applied; running validation only.")
        validate(root)
        return

    backup = create_backup(root)
    path = root / TARGET
    original = read_utf8(path)

    try:
        updated = original.rstrip() + FIX_BLOCK + "\n"
        path.write_text(updated, encoding="utf-8")
        validate(root)
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(root, backup)
        raise

    print(
        "APPLY OK: static/css/mobile.css updated; Home featured card now respects "
        "short desktop exhibition grid rows"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup-only", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--validate", action="store_true")
    group.add_argument("--rollback-last", action="store_true")
    args = parser.parse_args()

    root = project_root()

    if args.backup_only:
        create_backup(root)
    elif args.apply:
        apply_patch(root)
    elif args.validate:
        validate(root)
    elif args.rollback_last:
        restore_backup(root, latest_backup(root))


if __name__ == "__main__":
    main()
