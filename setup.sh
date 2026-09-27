#!/bin/bash

# Signal Analyzer - Quick Start Script

set -e

echo "=========================================="
echo "Signal Analyzer - Setup Script"
echo "=========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    WINDOWS=true
    VENV_BIN="venv\\Scripts"
else
    WINDOWS=false
    VENV_BIN="venv/bin"
fi

# Backend setup
echo "1️⃣  Setting up Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ "$WINDOWS" = true ]; then
    source venv/Scripts/activate.bat
else
    source venv/bin/activate
fi

# Install dependencies
echo "   Installing dependencies..."
pip install -r requirements.txt

# Setup .env
if [ ! -f ".env" ]; then
    echo "   Creating .env from template..."
    cp .env.example .env
    echo "   ⚠️  Please edit .env with your Telegram credentials!"
fi

# Initialize database
echo "   Initializing database..."
python -c "from app.database.base import init_db; init_db()"
echo "   ✓ Database initialized"

cd ..

# Frontend setup
echo ""
echo "2️⃣  Setting up Frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm install
fi

# Create .env.local if needed
if [ ! -f ".env.local" ]; then
    echo "   Creating .env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
fi

cd ..

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure Backend:"
echo "   - Edit backend/.env with your Telegram credentials"
echo "   - Get API credentials from https://my.telegram.org"
echo ""
echo "2. Start Backend:"
echo "   cd backend"
if [ "$WINDOWS" = true ]; then
    echo "   venv\\Scripts\\activate"
else
    echo "   source venv/bin/activate"
fi
echo "   python -m uvicorn app.main:app --reload"
echo ""
echo "3. Start Frontend (in another terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Open browser:"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
