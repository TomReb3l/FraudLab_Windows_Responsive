from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

TABLET_VIEWPORTS = [
    ("android_small_portrait", 800, 1280),
    ("android_small_landscape", 1280, 800),
    ("android_medium_portrait", 820, 1180),
    ("android_medium_landscape", 1180, 820),
    ("ipad_class_portrait", 834, 1194),
    ("ipad_class_landscape", 1194, 834),
    ("android_large_portrait", 1024, 1366),
    ("android_large_landscape", 1366, 1024),
]

CSS_MARKER = "/* QR ANDROID TABLET TOUCH SCROLL v1 */"
TEST_PROBE_ID = "__fraudlab_tablet_scroll_probe__"

ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 13; Tablet) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Safari/537.36"
)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def project_root() -> Path:
    root = Path.cwd()
    required = [
        root / "backend/main.py",
        root / "frontend/qr/index.html",
        root / "static/css/qr-simulation.css",
    ]
    for path in required:
        if not path.exists():
            fail(f"Missing expected project file: {path.relative_to(root)}")
    return root


def free_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.4)

    fail(f"Backend health check did not become ready: {last_error}")


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        fail(
            "Playwright is not installed in the project venv. Run: "
            r".\.venv\Scripts\python.exe -m pip install playwright"
        )


def launch_browsers(playwright):
    browsers = []
    errors = []

    try:
        browsers.append(
            ("msedge", playwright.chromium.launch(channel="msedge", headless=True))
        )
    except Exception as exc:
        errors.append(f"msedge: {exc}")

    try:
        browsers.append(
            ("playwright-chromium", playwright.chromium.launch(headless=True))
        )
    except Exception as exc:
        errors.append(f"playwright-chromium: {exc}")

    if not browsers:
        fail(
            "Could not launch Edge or Playwright Chromium.\n"
            "Run: .\\.venv\\Scripts\\python.exe -m playwright install chromium\n"
            + "\n".join(errors)
        )

    return browsers, errors


def inspect_viewport(
    browser,
    browser_name: str,
    base_url: str,
    name: str,
    width: int,
    height: int,
    failure_dir: Path,
):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        screen={"width": width, "height": height},
        has_touch=True,
        is_mobile=True,
        device_scale_factor=1,
        locale="el-GR",
        user_agent=ANDROID_UA,
    )

    page = context.new_page()
    screenshot = None

    try:
        page.goto(base_url + "/qr", wait_until="networkidle", timeout=30000)
        page.wait_for_selector(".qr-screen", timeout=15000)

        mail = page.locator(".challenge-layout--mail")
        if mail.count() == 0:
            start_button = page.locator("#startBtn")
            start_button.wait_for(state="visible", timeout=15000)
            start_button.click()

        page.wait_for_selector(
            ".challenge-layout--mail",
            state="visible",
            timeout=15000,
        )

        result = page.evaluate(
            f"""async () => {{
                const screen = document.querySelector('.qr-screen');
                const mail = document.querySelector('.challenge-layout--mail');
                const panel = document.querySelector('.left-panel--mail');
                const choice = document.querySelector('.choice-area--mail');
                const docScroller = document.scrollingElement || document.documentElement;

                if (!screen) return {{ error: 'missing .qr-screen' }};
                if (!mail) return {{ error: 'missing .challenge-layout--mail' }};

                const media = {{
                    coarse: matchMedia('(pointer: coarse)').matches,
                    noHover: matchMedia('(hover: none)').matches,
                    maxWidth1400: matchMedia('(max-width: 1400px)').matches,
                    maxHeight950: matchMedia('(max-height: 950px)').matches
                }};

                const originalScreenScroll = screen.scrollTop;
                const originalDocumentScroll = docScroller.scrollTop;

                const oldProbe = document.getElementById('{TEST_PROBE_ID}');
                if (oldProbe) oldProbe.remove();

                const probe = document.createElement('div');
                probe.id = '{TEST_PROBE_ID}';
                probe.setAttribute('aria-hidden', 'true');

                const forcedHeight = Math.max(
                    1600,
                    Math.round(window.innerHeight * 1.5)
                );

                probe.style.cssText = [
                    'display:block',
                    'width:1px',
                    `height:${{forcedHeight}}px`,
                    `min-height:${{forcedHeight}}px`,
                    `flex:0 0 ${{forcedHeight}}px`,
                    'grid-column:1 / -1',
                    'pointer-events:none',
                    'visibility:hidden'
                ].join(';');

                screen.appendChild(probe);

                await new Promise(resolve => requestAnimationFrame(() =>
                    requestAnimationFrame(resolve)
                ));

                const screenStyle = getComputedStyle(screen);
                const bodyStyle = getComputedStyle(document.body);
                const htmlStyle = getComputedStyle(document.documentElement);

                const screenClientHeight = screen.clientHeight;
                const screenScrollHeight = screen.scrollHeight;
                const screenMaxScroll = Math.max(
                    0,
                    screenScrollHeight - screenClientHeight
                );

                const documentScrollHeight = docScroller.scrollHeight;
                const documentMaxScroll = Math.max(
                    0,
                    documentScrollHeight - window.innerHeight
                );

                // Path A: dedicated .qr-screen scroller (typical landscape tablet).
                screen.scrollTop = screenMaxScroll;

                await new Promise(resolve => requestAnimationFrame(() =>
                    requestAnimationFrame(resolve)
                ));

                const screenScrollAfter = screen.scrollTop;
                let screenRect = screen.getBoundingClientRect();
                let probeRect = probe.getBoundingClientRect();

                const internalReachedBottom =
                    screenMaxScroll > 0 &&
                    Math.abs(screenScrollAfter - screenMaxScroll) <= 4 &&
                    probeRect.bottom <= screenRect.bottom + 5;

                // Restore the internal scroller before testing document scrolling.
                screen.scrollTop = originalScreenScroll;

                // Path B: document/window scroller (valid on portrait layouts that
                // naturally grow the .qr-screen instead of clipping it internally).
                window.scrollTo(0, documentMaxScroll);

                await new Promise(resolve => requestAnimationFrame(() =>
                    requestAnimationFrame(resolve)
                ));

                const documentScrollAfter = docScroller.scrollTop;
                probeRect = probe.getBoundingClientRect();

                const documentReachedBottom =
                    documentMaxScroll > 0 &&
                    Math.abs(documentScrollAfter - documentMaxScroll) <= 5 &&
                    probeRect.bottom <= window.innerHeight + 5;

                let scrollMode = 'none';
                if (internalReachedBottom && documentReachedBottom) {{
                    scrollMode = 'both';
                }} else if (internalReachedBottom) {{
                    scrollMode = 'qr-screen';
                }} else if (documentReachedBottom) {{
                    scrollMode = 'document';
                }}

                const result = {{
                    media,
                    overflowY: screenStyle.overflowY,
                    touchAction: screenStyle.touchAction,
                    bodyOverflowY: bodyStyle.overflowY,
                    htmlOverflowY: htmlStyle.overflowY,
                    viewportHeight: window.innerHeight,
                    viewportWidth: window.innerWidth,
                    forcedHeight,
                    screenClientHeight,
                    screenScrollHeight,
                    screenMaxScroll,
                    screenScrollAfter,
                    documentScrollHeight,
                    documentMaxScroll,
                    documentScrollAfter,
                    internalReachedBottom,
                    documentReachedBottom,
                    bottomReachable:
                        internalReachedBottom || documentReachedBottom,
                    scrollMode,
                    mailHeight: mail
                        ? Math.round(mail.getBoundingClientRect().height)
                        : null,
                    panelHeight: panel
                        ? Math.round(panel.getBoundingClientRect().height)
                        : null,
                    choiceHeight: choice
                        ? Math.round(choice.getBoundingClientRect().height)
                        : null
                }};

                probe.remove();
                screen.scrollTop = originalScreenScroll;
                window.scrollTo(0, originalDocumentScroll);

                return result;
            }}"""
        )

        if result.get("error"):
            passed = False
            reasons = [result["error"]]
        else:
            reasons = []

            tablet_media_ok = bool(
                result["media"]["coarse"] or result["media"]["noHover"]
            )

            patch_active = result["overflowY"] in ("auto", "scroll")

            forced_overflow_ok = (
                result["screenMaxScroll"] >= 300
                or result["documentMaxScroll"] >= 300
            )

            scroll_moved = (
                result["screenScrollAfter"] > 0
                or result["documentScrollAfter"] > 0
            )

            bottom_reachable = bool(result["bottomReachable"])

            touch_ok = (
                "pan-y" in (result["touchAction"] or "")
                or result["touchAction"] == "auto"
            )

            checks = [
                ("touch/coarse media query active", tablet_media_ok),
                ("tablet scroll CSS is active", patch_active),
                ("forced overflow exists in a valid scroll owner", forced_overflow_ok),
                ("a valid scroll owner moved", scroll_moved),
                ("bottom probe became reachable", bottom_reachable),
                ("touch-action permits vertical pan", touch_ok),
            ]

            for description, ok in checks:
                if not ok:
                    reasons.append(description)

            passed = not reasons

        if not passed:
            failure_dir.mkdir(parents=True, exist_ok=True)
            screenshot = (
                failure_dir
                / f"{browser_name}_{name}_{width}x{height}.png"
            )
            page.screenshot(path=str(screenshot), full_page=True)

        return passed, result, reasons, screenshot

    finally:
        context.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "FraudLab Station 3 tablet/touch scroll regression validator v2.2"
        )
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Use an already running FraudLab URL, e.g. http://127.0.0.1:8000",
    )
    args = parser.parse_args()

    root = project_root()

    css = (root / "static/css/qr-simulation.css").read_text(encoding="utf-8")
    if CSS_MARKER not in css:
        fail(
            "The Android/tablet touch-scroll patch marker is not present in "
            "static/css/qr-simulation.css"
        )

    server = None

    if args.base_url:
        base_url = args.base_url.rstrip("/")
        wait_for_health(base_url)
    else:
        port = free_port()
        base_url = f"http://127.0.0.1:{port}"

        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            wait_for_health(base_url)
        except Exception:
            server.terminate()
            raise

    sync_playwright = load_playwright()

    evidence_root = (
        root.parent
        / f"{root.name}_test_artifacts"
        / "tablet_layout_v2_2"
    )
    failure_dir = evidence_root / "failures"
    evidence_root.mkdir(parents=True, exist_ok=True)

    report = {
        "validator_version": "2.2",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "viewports": [],
        "browser_launch_warnings": [],
        "all_passed": True,
    }

    try:
        with sync_playwright() as p:
            browser_entries, launch_errors = launch_browsers(p)
            report["browser_launch_warnings"] = launch_errors

            try:
                for browser_name, browser in browser_entries:
                    print(f"BROWSER: {browser_name}")
                    print(f"URL: {base_url}/qr")

                    for name, width, height in TABLET_VIEWPORTS:
                        passed, details, reasons, screenshot = inspect_viewport(
                            browser,
                            browser_name,
                            base_url,
                            name,
                            width,
                            height,
                            failure_dir,
                        )

                        status = "PASS" if passed else "FAIL"

                        print(
                            f"{status:4}  {name:28} {width:4}x{height:<4} "
                            f"mode={details.get('scrollMode')} "
                            f"screenMax={details.get('screenMaxScroll')} "
                            f"docMax={details.get('documentMaxScroll')} "
                            f"bottom={details.get('bottomReachable')}"
                        )

                        if reasons:
                            for reason in reasons:
                                print(f"      - {reason}")

                        report["viewports"].append(
                            {
                                "browser": browser_name,
                                "name": name,
                                "width": width,
                                "height": height,
                                "passed": passed,
                                "reasons": reasons,
                                "details": details,
                                "failure_screenshot": (
                                    str(screenshot) if screenshot else None
                                ),
                            }
                        )

                        if not passed:
                            report["all_passed"] = False

                    print("")
            finally:
                for _, browser in browser_entries:
                    browser.close()

    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    report_path = evidence_root / "tablet_layout_report_v2_2.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"REPORT: {report_path}")

    if report["all_passed"]:
        print("TABLET SCROLL REGRESSION READY")
        raise SystemExit(0)

    print("TABLET SCROLL REGRESSION NOT READY")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
