@echo off
cd /d "%~dp0"

echo Starting app...
start "" cmd /k python app.py

echo Waiting for server to start...
timeout /t 3 /nobreak > nul

echo Opening browser...
start http://localhost:5000

