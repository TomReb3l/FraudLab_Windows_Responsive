@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo FraudLab Exhibition Launcher
echo ==========================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Expected: .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo Starting FraudLab backend...

start "FraudLab Backend" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

timeout /t 5 /nobreak >nul

echo Opening exhibition interface...

start "" "http://127.0.0.1:8000/"

echo FraudLab Exhibition started.
exit /b 0
