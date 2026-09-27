@echo off
REM Signal Analyzer - Quick Start Script for Windows

setlocal enabledelayedexpansion

echo ==========================================
echo Signal Analyzer - Setup Script
echo ==========================================
echo.

REM Backend setup
echo 1 - Setting up Backend...
cd backend

REM Create virtual environment
if not exist "venv" (
    echo    Creating virtual environment...
    python -m venv venv
)

REM Install dependencies
echo    Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM Setup .env
if not exist ".env" (
    echo    Creating .env from template...
    copy .env.example .env
    echo    WARNING: Please edit .env with your Telegram credentials!
)

REM Initialize database
echo    Initializing database...
python -c "from app.database.base import init_db; init_db()"
echo    Database initialized

cd ..

REM Frontend setup
echo.
echo 2 - Setting up Frontend...
cd frontend

if not exist "node_modules" (
    echo    Installing dependencies...
    call npm install
)

REM Create .env.local
if not exist ".env.local" (
    echo    Creating .env.local...
    (
        echo NEXT_PUBLIC_API_URL=http://localhost:8000
    ) > .env.local
)

cd ..

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo.
echo 1. Configure Backend:
echo    - Edit backend\.env with your Telegram credentials
echo    - Get API credentials from https://my.telegram.org
echo.
echo 2. Start Backend ^(in Command Prompt^):
echo    cd backend
echo    venv\Scripts\activate
echo    python -m uvicorn app.main:app --reload
echo.
echo 3. Start Frontend ^(in another Command Prompt^):
echo    cd frontend
echo    npm run dev
echo.
echo 4. Open browser:
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:8000/docs
echo.
