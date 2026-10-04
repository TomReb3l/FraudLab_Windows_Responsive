@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo ERROR: .venv\Scripts\pythonw.exe was not found.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "scripts\exhibition_launcher.py" stop --gui
exit /b 0
