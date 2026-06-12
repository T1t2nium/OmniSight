@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo ============================================
echo   OmniSight - Environment Setup
echo ============================================
echo.

echo [1/3] Setting up Python backend with uv...
cd backend
if not exist ".venv" (
    echo   Creating Python 3.11 virtual environment...
    uv venv --python 3.11
)
echo   Installing backend dependencies...
uv sync
cd ..

echo.
echo [2/3] Setting up frontend...
cd frontend
if not exist "node_modules" (
    echo   Installing npm packages...
    npm install
)
cd ..

echo.
echo [3/3] Verifying environment...
echo.
echo   Python:
cd backend
uv run python --version
cd ..
echo.
echo   Node:
node --version
echo   npm:
npm --version
echo.

echo ============================================
echo   Setup complete!
echo.
echo   Start backend:  scripts\run-backend.bat
echo   Start frontend: scripts\run-frontend.bat
echo ============================================
pause
