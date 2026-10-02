#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FraudLab Responsive Phase 1 - landscape + tablet compatibility patch.

Purpose:
- Keep the already validated phone portrait behaviour unchanged.
- Extend the same safe responsive overrides to phone landscape.
- Extend them to touch tablets in portrait and landscape, including large iPads.
- Preserve normal desktop/exhibition layouts by avoiding tablet-only activation
  on ordinary >768px fine-pointer desktop displays.

Supported starting states:
1) Phase 1 phone-only CSS (primary breakpoint: max-width 768px)
2) Previous phone-landscape patch
3) This patch already applied

Usage:
  python scripts/install_landscape_tablet_patch.py --backup-only
  python scripts/install_landscape_tablet_patch.py --apply
  python scripts/install_landscape_tablet_patch.py --validate
  python scripts/install_landscape_tablet_patch.py --rollback-last
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

PHONE_ONLY_MEDIA = "@media (max-width: 768px) {"
PHONE_LANDSCAPE_MEDIA = (
    "@media (max-width: 768px), "
    "(orientation: landscape) and (max-width: 1024px) and (max-height: 600px) {"
)
FINAL_MEDIA = (
    "@media (max-width: 768px), "
    "(orientation: landscape) and (max-width: 1024px) and (max-height: 600px), "
    "(min-width: 769px) and (max-width: 1024px) and (any-pointer: coarse), "
    "(orientation: landscape) and (min-width: 1025px) and (max-width: 1366px) "
    "and (max-height: 1024px) and (any-pointer: coarse) {"
)

FILES = (
    Path("static/css/mobile.css"),
    Path("static/css/call-mobile.css"),
    Path("static/css/sms-mobile.css"),
    Path("static/css/qr-mobile.css"),
)

EXPECTED_MARKERS = {
    Path("static/css/mobile.css"): "body.home-page",
    Path("static/css/call-mobile.css"): "body.call-page",
    Path("static/css/sms-mobile.css"): "body.sms-page",
    Path("static/css/qr-mobile.css"): "body.qr-page",
}

COMMENT_REPLACEMENTS = {
    Path("static/css/call-mobile.css"): (
        " Loaded after call.css. Rules apply only at <= 768px so the\n"
        " desktop/exhibition presentation remains unchanged.",
        " Loaded after call.css. Rules cover phones plus touch tablets while\n"
        " normal desktop/exhibition presentation remains unchanged.",
    ),
    Path("static/css/sms-mobile.css"): (
        " Loaded last. Rules are restricted to <= 768px and the sms-page scope so\n"
        " desktop/exhibition presentation and the other stations remain unchanged.",
        " Loaded last. Rules are scoped to sms-page and cover phones plus touch\n"
        " tablets while desktop/exhibition and other stations remain unchanged.",
    ),
    Path("static/css/qr-mobile.css"): (
        " Loaded last. Rules are restricted to <= 768px and the qr-page scope so\n"
        " desktop/exhibition presentation and the other stations remain unchanged.",
        " Loaded last. Rules are scoped to qr-page and cover phones plus touch\n"
        " tablets while desktop/exhibition and other stations remain unchanged.",
    ),
}


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
        root / "static/css/mobile.css",
        root / "static/css/call-mobile.css",
        root / "static/css/sms-mobile.css",
        root / "static/css/qr-mobile.css",
    ]
    missing = [p.relative_to(root) for p in required if not p.exists()]
    if missing:
        die(
            "Expected FraudLab_Windows_Responsive Phase 1 files are missing: "
            + ", ".join(str(p) for p in missing)
        )
    return root


def backup_root(root: Path) -> Path:
    return root.parent / f"{root.name}_backups" / "landscape_tablet"


def state_for_text(text: str, rel: Path) -> str:
    marker = EXPECTED_MARKERS[rel]
    if marker not in text:
        die(f"Unexpected CSS content in {rel}: marker {marker!r} not found")

    counts = {
        "phone_only": text.count(PHONE_ONLY_MEDIA),
        "phone_landscape": text.count(PHONE_LANDSCAPE_MEDIA),
        "final": text.count(FINAL_MEDIA),
    }
    active = [name for name, count in counts.items() if count == 1]
    invalid = [name for name, count in counts.items() if count > 1]
    if invalid or len(active) != 1:
        die(f"Unexpected primary media-query state in {rel}: {counts}")
    return active[0]


def inspect_state(root: Path) -> str:
    states: list[str] = []
    for rel in FILES:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        states.append(state_for_text(text, rel))
    if len(set(states)) != 1:
        die(f"Mixed responsive patch state across CSS files: {states}")
    return states[0]


def create_backup(root: Path) -> Path:
    state = inspect_state(root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = backup_root(root) / stamp
    dest.mkdir(parents=True, exist_ok=False)

    manifest = {
        "created": stamp,
        "state": state,
        "files": [rel.as_posix() for rel in FILES],
    }
    for rel in FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target)

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

        for rel in FILES:
            url = "/" + rel.as_posix()
            response = client.get(url)
            if response.status_code != 200:
                die(f"Static CSS validation failed: {url} -> HTTP {response.status_code}")
            if FINAL_MEDIA not in response.text:
                die(f"Landscape/tablet media query not served in {url}")
    except SystemExit:
        raise
    except Exception as exc:
        die(f"Runtime validation failed: {exc}")


def validate(root: Path) -> None:
    state = inspect_state(root)
    if state != "final":
        die("Landscape/tablet patch is not in the expected applied state")

    for rel in FILES:
        text = (root / rel).read_text(encoding="utf-8")
        if text.count(FINAL_MEDIA) != 1:
            die(f"Expected exactly one final responsive media query in {rel}")
        if "@media (max-width: 480px) {" not in text:
            die(f"Existing <=480px fine-tuning block missing in {rel}")
        if PHONE_ONLY_MEDIA in text or PHONE_LANDSCAPE_MEDIA in text:
            die(f"Obsolete primary media query still present in {rel}")

    validate_json(root)
    validate_runtime(root)
    print(
        "VALIDATION OK: Phase 1 phone portrait, phone landscape and touch-tablet "
        "responsive breakpoints, UTF-8, JSON, FastAPI routes and CSS assets"
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
        die("No landscape_tablet backup directory exists")
    backups = sorted(p for p in base.iterdir() if p.is_dir())
    if not backups:
        die("No landscape_tablet backups found")
    return backups[-1]


def update_comment(text: str, rel: Path) -> str:
    pair = COMMENT_REPLACEMENTS.get(rel)
    if not pair:
        return text
    old, new = pair
    if old in text:
        return text.replace(old, new, 1)
    # If the new wording is already present (e.g. re-run), keep it.
    if new in text:
        return text
    # Comments are non-functional, so don't risk modifying unknown text.
    return text


def apply_patch(root: Path) -> None:
    state = inspect_state(root)
    if state == "final":
        print("INFO: Landscape/tablet patch is already applied; running validation only.")
        validate(root)
        return

    backup = create_backup(root)
    try:
        source_media = PHONE_ONLY_MEDIA if state == "phone_only" else PHONE_LANDSCAPE_MEDIA
        for rel in FILES:
            path = root / rel
            text = path.read_text(encoding="utf-8")
            if text.count(source_media) != 1:
                die(f"Expected one {state} primary media query in {rel}")
            text = text.replace(source_media, FINAL_MEDIA, 1)
            text = update_comment(text, rel)
            path.write_text(text, encoding="utf-8", newline="\n")

        validate(root)
        print(
            "APPLY OK: Home, Call, SMS and QR responsive overrides now cover phone "
            "portrait, phone landscape and touch tablets without changing normal "
            "desktop/exhibition breakpoints"
        )
    except BaseException:
        print("ERROR: Apply/validation failed. Restoring the backup automatically.")
        restore_backup(root, backup)
        raise


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
