@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set LOG_DIR=%~dp0logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ========================================== >> "%LOG_DIR%\fraudlab_lan_startup.log"
echo FraudLab LAN Startup %date% %time% >> "%LOG_DIR%\fraudlab_lan_startup.log"
echo ========================================== >> "%LOG_DIR%\fraudlab_lan_startup.log"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment missing.
    pause
    exit /b 1
)

echo Starting FraudLab LAN backend...

start "FraudLab Backend LAN" /min cmd /c ".venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 >> logs\backend.log 2>&1"

timeout /t 5 /nobreak >nul

start "" "http://192.168.0.100:8000/"

echo FraudLab LAN started successfully.
echo Mobile access:
echo http://192.168.0.100:8000/

exit /b 0
