@echo off
cd /d "%~dp0"
echo Starting UtilityAI frontend on http://localhost:5500
python frontend_server.py
pause
