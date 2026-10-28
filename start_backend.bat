@echo off
cd /d "%~dp0"
echo Starting UtilityAI API on http://localhost:8001
set SERVE_FRONTEND=0
python -m uvicorn main:app --host 0.0.0.0 --port 8001
if errorlevel 1 echo API failed to start. Check whether port 8001 is already in use and verify dependencies.
pause
