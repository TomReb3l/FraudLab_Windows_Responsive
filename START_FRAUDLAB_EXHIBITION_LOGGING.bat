@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set LOG_DIR=%~dp0logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set LOG_FILE=%LOG_DIR%\fraudlab_startup.log

echo ========================================== >> "%LOG_FILE%"
echo FraudLab Startup %date% %time% >> "%LOG_FILE%"
echo ========================================== >> "%LOG_FILE%"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment missing >> "%LOG_FILE%"
    echo ERROR: Virtual environment not found.
    pause
    exit /b 1
)

echo Starting FraudLab backend... >> "%LOG_FILE%"

start "FraudLab Backend" /min cmd /c ".venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 >> logs\backend.log 2>&1"

timeout /t 5 /nobreak >nul

echo Opening exhibition interface... >> "%LOG_FILE%"

start "" "http://127.0.0.1:8000/"

echo FraudLab started successfully >> "%LOG_FILE%"

exit /b 0
