#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FraudLab Windows exhibition launcher runtime.

Pure-stdlib Windows controller for the public exhibition build.
It owns only processes that it starts and never kills an unknown process.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"http://{HOST}:{PORT}/api/health"
STARTUP_TIMEOUT_SECONDS = 30.0
HEALTH_INTERVAL_SECONDS = 0.5
MUTEX_NAME = r"Local\FraudLabExhibitionLauncherV6"
WATCHDOG_MUTEX_NAME = r"Local\FraudLabExhibitionWatchdogV6"
WATCHDOG_INTERVAL_SECONDS = 5.0
WATCHDOG_FAILURE_THRESHOLD = 3
WATCHDOG_RESTART_WINDOW_SECONDS = 180.0
WATCHDOG_MAX_RESTARTS = 3
WATCHDOG_COOLDOWN_SECONDS = 120.0

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
STATE_FILE = LOG_DIR / "exhibition_runtime.tmp"
LAUNCHER_LOG = LOG_DIR / "exhibition_launcher.log"

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
ERROR_ALREADY_EXISTS = 183
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259


def _logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fraudlab.exhibition")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LAUNCHER_LOG,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


LOG = _logger()


def message_box(text: str, title: str = "FraudLab Exhibition Launcher", error: bool = True) -> None:
    if os.name != "nt":
        return
    flags = 0x10 if error else 0x40
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        pass


def fail(message: str, *, gui: bool = False, code: int = 1) -> int:
    LOG.error(message)
    if not gui:
        print(f"ERROR: {message}", file=sys.stderr)
    if gui:
        message_box(message, error=True)
    return code


def write_state(state: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, STATE_FILE)


def read_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"schema": 1}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as exc:
        LOG.warning("Ignoring unreadable runtime state: %s", exc)
    return {"schema": 1}


def clear_state() -> None:
    try:
        STATE_FILE.unlink(missing_ok=True)
    except Exception as exc:
        LOG.warning("Could not remove runtime state: %s", exc)


def find_edge() -> Path | None:
    candidates: list[Path] = []
    on_path = shutil.which("msedge.exe") or shutil.which("msedge")
    if on_path:
        candidates.append(Path(on_path))
    for env_name in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def python_executable() -> Path:
    path = ROOT / ".venv" / "Scripts" / "python.exe"
    return path


def edge_profile_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not available")
    return Path(local_app_data) / "FraudLab" / "EdgeKioskProfile"


def validate_project_files() -> list[str]:
    required = [
        ROOT / "backend" / "main.py",
        ROOT / "backend" / "config.py",
        ROOT / "frontend" / "home" / "index.html",
        ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    return [str(p.relative_to(ROOT)) for p in required if not p.is_file()]


def forced_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "FRAUDLAB_MODE": "exhibition",
            "ENABLE_AI": "false",
            "OFFLINE_MODE": "true",
            "DEBUG_MODE": "false",
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return env


def health_check(timeout: float = 1.5) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        request = Request(HEALTH_URL, headers={"Cache-Control": "no-cache"})
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return False, None, f"HTTP {response.status}"
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return False, None, str(exc)
    if not isinstance(payload, dict):
        return False, None, "Health response is not a JSON object"
    status_ok = str(payload.get("status", "")).lower() == "ok"
    ai_disabled = str(payload.get("ai_enabled", "")).lower() in {"false", "0", "no", "off"}
    mode_ok = str(payload.get("mode", "")).lower() == "offline-first"
    if not (status_ok and ai_disabled and mode_ok):
        return False, payload, "Health response does not match exhibition safety policy"
    return True, payload, None


def port_open(timeout: float = 0.35) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((HOST, PORT)) == 0


def _windows_process_info(pid: int) -> dict[str, Any] | None:
    if os.name != "nt" or pid <= 0:
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None
        if exit_code.value != STILL_ACTIVE:
            return None

        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None

        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        creation_value = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        return {
            "pid": pid,
            "image_path": str(Path(buffer.value).resolve()),
            "creation_time": int(creation_value),
        }
    finally:
        kernel32.CloseHandle(handle)


def process_info(pid: int) -> dict[str, Any] | None:
    if os.name == "nt":
        return _windows_process_info(pid)
    return None


def process_matches(record: dict[str, Any] | None) -> bool:
    if not record or not record.get("owned"):
        return False
    try:
        pid = int(record["pid"])
        creation_time = int(record["creation_time"])
        expected_path = str(record["image_path"])
    except (KeyError, TypeError, ValueError):
        return False
    current = process_info(pid)
    if not current:
        return False
    return (
        int(current["creation_time"]) == creation_time
        and os.path.normcase(str(current["image_path"])) == os.path.normcase(expected_path)
    )


def process_record(pid: int, *, owned: bool, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not owned:
        result: dict[str, Any] = {"owned": False}
    else:
        info = None
        for _ in range(20):
            info = process_info(pid)
            if info:
                break
            time.sleep(0.05)
        if not info:
            raise RuntimeError(f"Could not verify process identity for PID {pid}")
        result = {"owned": True, **info}
    if extra:
        result.update(extra)
    return result


def _hidden_subprocess_flags() -> int:
    return CREATE_NO_WINDOW if os.name == "nt" else 0


def terminate_owned_process(record: dict[str, Any] | None, label: str, timeout: float = 5.0) -> bool:
    if not process_matches(record):
        LOG.info("%s is not an owned live process; nothing to terminate", label)
        return True
    pid = int(record["pid"])
    LOG.info("Stopping owned %s process PID %s", label, pid)
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_hidden_subprocess_flags(),
            check=False,
        )
    except OSError as exc:
        LOG.warning("Graceful taskkill failed for %s PID %s: %s", label, pid, exc)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_matches(record):
            return True
        time.sleep(0.25)

    LOG.warning("%s PID %s did not exit; forcing termination", label, pid)
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_hidden_subprocess_flags(),
            check=False,
        )
    except OSError as exc:
        LOG.error("Forced taskkill failed for %s PID %s: %s", label, pid, exc)
        return False

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if not process_matches(record):
            return True
        time.sleep(0.25)
    return not process_matches(record)


def acquire_named_mutex(name: str) -> int | None:
    if os.name != "nt":
        return 1
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return None
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return int(handle)


def acquire_mutex() -> int | None:
    return acquire_named_mutex(MUTEX_NAME)


def acquire_watchdog_mutex() -> int | None:
    return acquire_named_mutex(WATCHDOG_MUTEX_NAME)


def release_mutex(handle: int | None) -> None:
    if os.name == "nt" and handle:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(handle)


def prune_backend_logs(keep: int = 10) -> None:
    logs = sorted(LOG_DIR.glob("backend_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in logs[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


def launch_backend() -> tuple[subprocess.Popen[Any], dict[str, Any]]:
    py = python_executable()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backend_log = LOG_DIR / f"backend_{stamp}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    prune_backend_logs()

    command = [
        str(py),
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--no-access-log",
        "--log-level",
        "info",
    ]
    LOG.info("Starting backend on %s:%s", HOST, PORT)
    log_handle = backend_log.open("ab", buffering=0)
    log_handle.write((f"\n===== FraudLab backend start {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n").encode("utf-8"))
    try:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=forced_environment(),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0,
        )
    finally:
        log_handle.close()
    record = process_record(
        process.pid,
        owned=True,
        extra={"log": str(backend_log.relative_to(ROOT)), "started": time.strftime("%Y-%m-%dT%H:%M:%S")},
    )
    return process, record


def wait_for_health(process: subprocess.Popen[Any] | None) -> tuple[bool, str]:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error = "Backend did not answer"
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False, f"Backend exited during startup with code {process.returncode}"
        healthy, payload, error = health_check()
        if healthy:
            return True, json.dumps(payload, ensure_ascii=False)
        if error:
            last_error = error
        time.sleep(HEALTH_INTERVAL_SECONDS)
    return False, f"Health timeout after {STARTUP_TIMEOUT_SECONDS:.0f}s: {last_error}"


def launch_edge(edge: Path) -> dict[str, Any]:
    profile = edge_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        str(edge),
        "--kiosk",
        BASE_URL,
        "--edge-kiosk-type=fullscreen",
        "--kiosk-idle-timeout-minutes=0",
        "--no-first-run",
        f"--user-data-dir={profile}",
    ]
    LOG.info("Opening Microsoft Edge kiosk: %s", BASE_URL)
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    time.sleep(0.75)
    if process.poll() is not None:
        raise RuntimeError(f"Microsoft Edge exited immediately with code {process.returncode}")
    return process_record(
        process.pid,
        owned=True,
        extra={"started": time.strftime("%Y-%m-%dT%H:%M:%S")},
    )


def launch_watchdog() -> tuple[subprocess.Popen[Any], dict[str, Any]]:
    command = [
        str(python_executable()),
        str(Path(__file__).resolve()),
        "watchdog",
    ]
    LOG.info("Starting backend watchdog")
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=forced_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0,
    )
    time.sleep(0.35)
    if process.poll() is not None:
        raise RuntimeError(f"Watchdog exited immediately with code {process.returncode}")
    record = process_record(
        process.pid,
        owned=True,
        extra={"started": time.strftime("%Y-%m-%dT%H:%M:%S")},
    )
    LOG.info("Backend watchdog started with PID %s", record.get("pid"))
    return process, record


def ensure_watchdog(state: dict[str, Any]) -> tuple[bool, str | None]:
    watchdog_record = state.get("watchdog")
    if process_matches(watchdog_record):
        LOG.info("Owned backend watchdog is already running")
        return True, None
    try:
        _process, watchdog_record = launch_watchdog()
        state["watchdog"] = watchdog_record
        write_state(state)
        return True, None
    except Exception as exc:
        state.pop("watchdog", None)
        write_state(state)
        return False, str(exc)


def watchdog_recover_backend() -> tuple[bool, bool]:
    """Return (attempted_restart, healthy_after_action)."""
    mutex = acquire_mutex()
    if mutex is None:
        LOG.info("WATCHDOG: launcher action is active; recovery deferred")
        return False, False
    try:
        healthy, payload, _error = health_check()
        if healthy:
            LOG.info("WATCHDOG: backend recovered before restart was required: %s", payload)
            return False, True

        state = read_state()
        owned_backend = state.get("backend")
        if process_matches(owned_backend):
            LOG.warning("WATCHDOG: stopping owned unhealthy backend before recovery")
            if not terminate_owned_process(owned_backend, "backend"):
                LOG.error("WATCHDOG: could not terminate owned unhealthy backend")
                return True, False
            state.pop("backend", None)
            write_state(state)
            time.sleep(0.5)

        if port_open():
            LOG.error(
                "WATCHDOG: port %s is occupied by an invalid/unhealthy endpoint; "
                "no unknown process will be terminated",
                PORT,
            )
            return True, False

        process: subprocess.Popen[Any] | None = None
        backend_record: dict[str, Any] | None = None
        try:
            process, backend_record = launch_backend()
            state = read_state()
            state["backend"] = backend_record
            write_state(state)
            ready, detail = wait_for_health(process)
            if not ready:
                terminate_owned_process(backend_record, "backend")
                state = read_state()
                current = state.get("backend")
                if (
                    isinstance(current, dict)
                    and current.get("pid") == backend_record.get("pid")
                    and current.get("creation_time") == backend_record.get("creation_time")
                ):
                    state.pop("backend", None)
                    write_state(state)
                LOG.error("WATCHDOG: backend recovery failed: %s", detail)
                return True, False
            LOG.info("WATCHDOG: backend recovery succeeded: %s", detail)
            return True, True
        except Exception as exc:
            if backend_record is not None:
                terminate_owned_process(backend_record, "backend")
            LOG.exception("WATCHDOG: backend recovery raised an exception: %s", exc)
            return True, False
    finally:
        release_mutex(mutex)


def watchdog() -> int:
    if os.name != "nt":
        return fail("The exhibition watchdog is supported on Windows only.")

    watchdog_mutex = acquire_watchdog_mutex()
    if watchdog_mutex is None:
        LOG.info("WATCHDOG: another watchdog instance is already running; duplicate exited")
        return 0

    consecutive_failures = 0
    restart_attempts: list[float] = []
    LOG.info(
        "WATCHDOG: active (interval=%.0fs, threshold=%s, max_restarts=%s/%ss, cooldown=%ss)",
        WATCHDOG_INTERVAL_SECONDS,
        WATCHDOG_FAILURE_THRESHOLD,
        WATCHDOG_MAX_RESTARTS,
        int(WATCHDOG_RESTART_WINDOW_SECONDS),
        int(WATCHDOG_COOLDOWN_SECONDS),
    )

    try:
        while True:
            try:
                healthy, _payload, error = health_check()
                if healthy:
                    if consecutive_failures:
                        LOG.info("WATCHDOG: health restored without restart")
                    consecutive_failures = 0
                    time.sleep(WATCHDOG_INTERVAL_SECONDS)
                    continue

                consecutive_failures += 1
                LOG.warning(
                    "WATCHDOG: health failure %s/%s: %s",
                    consecutive_failures,
                    WATCHDOG_FAILURE_THRESHOLD,
                    error or "unknown health failure",
                )
                if consecutive_failures < WATCHDOG_FAILURE_THRESHOLD:
                    time.sleep(WATCHDOG_INTERVAL_SECONDS)
                    continue

                now = time.monotonic()
                restart_attempts = [
                    stamp
                    for stamp in restart_attempts
                    if now - stamp <= WATCHDOG_RESTART_WINDOW_SECONDS
                ]
                if len(restart_attempts) >= WATCHDOG_MAX_RESTARTS:
                    LOG.error(
                        "WATCHDOG: restart limit reached (%s attempts in %ss); cooling down for %ss",
                        WATCHDOG_MAX_RESTARTS,
                        int(WATCHDOG_RESTART_WINDOW_SECONDS),
                        int(WATCHDOG_COOLDOWN_SECONDS),
                    )
                    consecutive_failures = 0
                    time.sleep(WATCHDOG_COOLDOWN_SECONDS)
                    restart_attempts.clear()
                    continue

                attempted, recovered = watchdog_recover_backend()
                if attempted:
                    restart_attempts.append(time.monotonic())
                consecutive_failures = 0
                if recovered:
                    LOG.info("WATCHDOG: backend is healthy after recovery")
                elif attempted:
                    LOG.error("WATCHDOG: recovery attempt did not restore backend health")

                time.sleep(WATCHDOG_INTERVAL_SECONDS)
            except Exception as exc:
                LOG.exception("WATCHDOG: unexpected loop error: %s", exc)
                consecutive_failures = 0
                time.sleep(max(WATCHDOG_INTERVAL_SECONDS, 10.0))
    finally:
        release_mutex(watchdog_mutex)


def start(*, gui: bool, no_browser: bool) -> int:
    if os.name != "nt":
        return fail("The exhibition launcher is supported on Windows only.", gui=gui)
    mutex = acquire_mutex()
    if mutex is None:
        LOG.info("Another launcher action is already running; duplicate request ignored")
        return 0
    try:
        missing = validate_project_files()
        if missing:
            return fail("Required project files are missing: " + ", ".join(missing), gui=gui)

        edge = None if no_browser else find_edge()
        if not no_browser and edge is None:
            return fail("Microsoft Edge was not found. The backend was not started.", gui=gui)

        state = read_state()
        healthy, payload, health_error = health_check()
        if healthy:
            LOG.info("Existing FraudLab backend is healthy: %s", payload)
            backend = state.get("backend")
            if not process_matches(backend):
                state["backend"] = {"owned": False, "note": "Healthy backend already existed"}
        else:
            owned_backend = state.get("backend")
            if process_matches(owned_backend):
                LOG.warning("Owned backend is alive but unhealthy; restarting it safely")
                if not terminate_owned_process(owned_backend, "backend"):
                    return fail("Could not stop the previous owned backend process.", gui=gui)
                time.sleep(0.5)

            if port_open():
                return fail(
                    f"Port {PORT} is already in use, but {HEALTH_URL} is not a valid FraudLab exhibition health endpoint. "
                    "No process was terminated.",
                    gui=gui,
                )

            process: subprocess.Popen[Any] | None = None
            try:
                process, backend_record = launch_backend()
                state = {"schema": 1, "backend": backend_record}
                write_state(state)
                ready, detail = wait_for_health(process)
                if not ready:
                    terminate_owned_process(backend_record, "backend")
                    clear_state()
                    return fail(detail + f". Check {backend_record.get('log', 'backend log')}.", gui=gui)
                LOG.info("Backend health check passed: %s", detail)
            except Exception as exc:
                if state.get("backend"):
                    terminate_owned_process(state.get("backend"), "backend")
                clear_state()
                return fail(f"Backend startup failed: {exc}", gui=gui)

        if no_browser:
            watchdog_ok, watchdog_error = ensure_watchdog(state)
            if not watchdog_ok:
                return fail(f"Backend is healthy, but watchdog could not be started: {watchdog_error}", gui=gui)
            write_state(state)
            if not gui:
                print("BACKEND READY")
            return 0

        browser_record = state.get("browser")
        if process_matches(browser_record):
            LOG.info("Owned Edge kiosk is already running; duplicate browser launch skipped")
        else:
            try:
                state["browser"] = launch_edge(edge)  # type: ignore[arg-type]
                write_state(state)
            except Exception as exc:
                return fail(f"Backend is healthy, but Microsoft Edge kiosk could not be opened: {exc}", gui=gui)

        watchdog_ok, watchdog_error = ensure_watchdog(state)
        if not watchdog_ok:
            return fail(f"FraudLab is running, but backend watchdog could not be started: {watchdog_error}", gui=gui)

        write_state(state)
        LOG.info("FraudLab exhibition startup complete")
        return 0
    finally:
        release_mutex(mutex)


def stop(*, gui: bool) -> int:
    if os.name != "nt":
        return fail("The exhibition launcher is supported on Windows only.", gui=gui)

    state = read_state()
    watchdog_ok = terminate_owned_process(state.get("watchdog"), "backend watchdog")

    mutex = None
    deadline = time.monotonic() + 8.0
    while mutex is None and time.monotonic() < deadline:
        mutex = acquire_mutex()
        if mutex is None:
            time.sleep(0.2)
    if mutex is None:
        return fail(
            "Could not obtain launcher control after stopping the watchdog. Try STOP again.",
            gui=gui,
        )

    try:
        state = read_state()
        browser_ok = terminate_owned_process(state.get("browser"), "Edge kiosk")
        backend_ok = terminate_owned_process(state.get("backend"), "backend")
        if watchdog_ok and browser_ok and backend_ok:
            clear_state()
            LOG.info("FraudLab exhibition processes stopped")
            if not gui:
                print("EXHIBITION STOPPED")
            return 0
        return fail("One or more owned exhibition processes could not be stopped. Check the launcher log.", gui=gui)
    finally:
        release_mutex(mutex)


def validate() -> int:
    errors: list[str] = []
    if os.name != "nt":
        errors.append("Windows is required")
    missing = validate_project_files()
    if missing:
        errors.append("Missing: " + ", ".join(missing))
    if find_edge() is None:
        errors.append("Microsoft Edge executable was not found")
    try:
        profile = edge_profile_dir()
    except RuntimeError as exc:
        errors.append(str(exc))
        profile = None

    py = python_executable()
    if py.is_file():
        check_code = (
            "import os; "
            "os.environ['FRAUDLAB_MODE']='exhibition'; "
            "os.environ['ENABLE_AI']='false'; "
            "os.environ['OFFLINE_MODE']='true'; "
            "os.environ['DEBUG_MODE']='false'; "
            "import uvicorn; from backend.main import health; "
            "h=health(); "
            "assert h.get('status')=='ok', h; "
            "assert str(h.get('ai_enabled')).lower()=='false', h; "
            "print('BACKEND IMPORT OK')"
        )
        try:
            result = subprocess.run(
                [str(py), "-c", check_code],
                cwd=str(ROOT),
                env=forced_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_hidden_subprocess_flags(),
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                errors.append("Backend import/health validation failed: " + result.stdout.strip())
        except Exception as exc:
            errors.append(f"Backend import/health validation failed: {exc}")

    if port_open():
        healthy, payload, error = health_check()
        if not healthy:
            errors.append(f"Port {PORT} is occupied by an invalid/unhealthy endpoint: {error or payload}")

    if errors:
        print("LAUNCHER NOT READY")
        for item in errors:
            print(f"- {item}")
        return 1

    print("LAUNCHER READY")
    print(f"- Project: {ROOT}")
    print(f"- Python: {py}")
    print(f"- Edge: {find_edge()}")
    print(f"- Edge profile: {profile}")
    print(f"- URL: {BASE_URL}")
    print("- Policy: exhibition / offline / AI disabled / debug disabled / backend watchdog enabled")
    return 0


def status() -> int:
    healthy, payload, error = health_check()
    state = read_state()
    watchdog_running = process_matches(state.get("watchdog"))
    print("HEALTHY" if healthy else "NOT HEALTHY")
    print("WATCHDOG RUNNING" if watchdog_running else "WATCHDOG NOT RUNNING")
    print(json.dumps(payload if payload is not None else {"error": error}, ensure_ascii=False, indent=2))
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if healthy and watchdog_running else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="FraudLab Windows exhibition launcher")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--gui", action="store_true", help="Show Windows message box on fatal error")
    p_start.add_argument("--no-browser", action="store_true", help="Start/verify backend without opening Edge")

    p_stop = sub.add_parser("stop")
    p_stop.add_argument("--gui", action="store_true", help="Show Windows message box on fatal error")

    sub.add_parser("watchdog")
    sub.add_parser("validate")
    sub.add_parser("status")

    args = parser.parse_args()
    if args.command == "start":
        return start(gui=args.gui, no_browser=args.no_browser)
    if args.command == "stop":
        return stop(gui=args.gui)
    if args.command == "watchdog":
        return watchdog()
    if args.command == "validate":
        return validate()
    if args.command == "status":
        return status()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
