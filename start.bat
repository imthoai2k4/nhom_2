@echo off
echo ============================================
echo   Cai dat dependencies - De tai 48
echo ============================================
pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2" python-dotenv openai python-multipart pytest
echo.
echo ============================================
echo   Khoi dong server
echo ============================================
python main.py
pause
