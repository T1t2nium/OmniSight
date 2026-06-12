@echo off
cd /d "%~dp0..\backend"
echo Starting OmniSight backend...
echo.
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
