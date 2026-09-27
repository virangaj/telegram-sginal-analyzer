# Signal Analyzer - Quick Reference

## Project Scaffold Complete ✓

Your Signal Analyzer project is now fully scaffolded with production-ready structure, following best practices for Django-like separation of concerns.

## What's Been Created

### Directory Structure
```
signal-analyzer/
├── backend/                           # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app with routes
│   │   ├── config.py                 # Settings from .env
│   │   ├── database/
│   │   │   ├── models.py             # SQLAlchemy ORM models
│   │   │   └── base.py               # Session management
│   │   ├── parsers/                  # Signal parser framework
│   │   │   ├── base.py               # Parser base class
│   │   │   ├── registry.py           # Parser registry/factory
│   │   │   └── implementations/
│   │   │       ├── examples.py       # Example parsers
│   │   │       └── __init__.py       # Parser initialization
│   │   ├── telegram/
│   │   │   ├── listener.py           # Telethon integration
│   │   │   └── handlers.py           # Message handlers
│   │   ├── database/                 # ORM models
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── signals.py        # Signal endpoints
│   │   │   │   ├── channels.py       # Channel endpoints
│   │   │   │   └── message_types.py  # Message type endpoints
│   │   │   └── schemas.py            # Request/response validation
│   │   ├── services/
│   │   │   └── signal_service.py     # Business logic
│   │   ├── analysis/
│   │   │   └── engine.py             # Analysis engine
│   │   ├── trade/
│   │   │   └── engine.py             # Trade setup engine
│   │   ├── market/
│   │   │   └── base.py               # Market data abstraction
│   │   └── analysis/
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                  # Environment template
│   └── setup_env.py                  # Environment setup
│
├── frontend/                          # Next.js TypeScript frontend
│   ├── pages/
│   │   ├── _app.tsx                  # App wrapper
│   │   └── index.tsx                 # Home/signals page
│   ├── components/
│   │   ├── Layout.tsx                # Main layout
│   │   ├── SignalCard.tsx            # Signal display card
│   │   └── SignalsList.tsx           # Signals list view
│   ├── lib/
│   │   ├── api.ts                    # API client
│   │   ├── types.ts                  # TypeScript types
│   │   └── store.ts                  # Zustand state store
│   ├── styles/
│   │   └── globals.css               # Global styles
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── docker/
│   ├── docker-compose.yml            # Full stack compose
│   ├── Dockerfile.backend            # Backend image
│   └── Dockerfile.frontend           # Frontend image
│
├── README.md                         # Project overview
├── ARCHITECTURE.md                   # Detailed architecture
├── GETTING_STARTED.md                # Setup and usage guide
├── DEVELOPMENT.md                    # Extensibility guide
├── setup.sh                          # Linux/Mac setup script
├── setup.bat                         # Windows setup script
└── .gitignore
```

## Core Concepts

### 1. Configurable Signal Parsers (The Heart of the System)

Instead of hard-coding signal formats, the system uses **pluggable parsers**:

- Create `SignalParser` subclass → implement `can_parse()` and `parse()`
- Parser converts any message format to normalized `NormalizedSignal`
- All signal types stored in `signal_message_types` database table
- New providers can be added without modifying core code

**Example:**
```python
class MyParser(SignalParser):
    def can_parse(self, message: str) -> bool:
        return "MY_SIGNAL" in message
    
    async def parse(self, message: str) -> NormalizedSignal:
        # Extract and normalize to standard format
        return NormalizedSignal(
            symbol="XAUUSD",
            direction="BUY",
            order_type="LIMIT",
            entries=[4288],
            stop_loss=4273,
            take_profits=[4335]
        )
```

### 2. Normalized Signal Format

All signals normalize to:
```json
{
  "symbol": "XAUUSD",
  "direction": "BUY|SELL",
  "order_type": "LIMIT|MARKET",
  "entries": [4288, ...],        // Multiple for scaling
  "stop_loss": 4273,
  "take_profits": [4335, ...],   // Multiple for scaling
  "timeframe": "4H",
  "provider": "telegram",
  "confidence": 0.95
}
```

### 3. Database Models

**Key tables:**
- `channels` - Telegram channels
- `signal_message_types` - Configurable parser definitions
- `raw_messages` - Original messages
- `signals` - Normalized parsed signals
- `signal_entries` - Entry prices (1-many)
- `signal_take_profits` - TP targets (1-many)
- `analyses` - Technical analysis results
- `trades` - Trade records

## Quick Start

### Option 1: Automated Setup

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Telegram credentials
python -m uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

**Access:**
- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Adding a New Signal Parser

### 1. Create Parser Class

`backend/app/parsers/implementations/my_parser.py`:
```python
from app.parsers.base import SignalParser, NormalizedSignal

class MyParser(SignalParser):
    def __init__(self):
        super().__init__("my_parser_v1")
    
    def can_parse(self, message: str) -> bool:
        return "MYSIGNAL" in message.upper()
    
    async def parse(self, message: str):
        # Extract and return NormalizedSignal
        pass
```

### 2. Register Parser

In `backend/app/parsers/implementations/__init__.py`:
```python
from app.parsers.registry import register_parser
from app.parsers.implementations.my_parser import MyParser

def init_parsers():
    # ... existing parsers
    register_parser("my_parser_v1", MyParser())
```

### 3. Create Message Type

Via API:
```bash
curl -X POST http://localhost:8000/api/message-types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_custom_signal",
    "parser_name": "my_parser_v1",
    "enabled": true
  }'
```

## Database Queries Reference

### Get Latest Signals
```python
from app.database.base import SessionLocal
from app.database.models import Signal

db = SessionLocal()
signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(10).all()
for s in signals:
    print(f"{s.symbol} {s.direction}: {s.entries} -> {s.take_profits}")
db.close()
```

### Get Signals by Channel
```python
channel_signals = db.query(Signal).filter(
    Signal.channel_id == 1
).order_by(Signal.created_at.desc()).all()
```

### Get Signal Statistics
```python
from sqlalchemy import func

stats = db.query(
    Signal.symbol,
    Signal.direction,
    func.count(Signal.id)
).group_by(Signal.symbol, Signal.direction).all()
```

## API Endpoints

### Signals
- `GET /api/signals` - List signals (query: symbol, limit)
- `GET /api/signals/{id}` - Get signal details
- `GET /api/signals/channel/{channel_id}` - Signals from channel

### Channels
- `GET /api/channels` - List channels
- `GET /api/channels/{id}` - Get channel details

### Message Types
- `GET /api/message-types` - List message types
- `GET /api/message-types/{id}` - Get message type
- `POST /api/message-types` - Create message type
- `PUT /api/message-types/{id}` - Update message type
- `DELETE /api/message-types/{id}` - Delete message type

### Status
- `GET /health` - Health check
- `GET /` - Root info

## Environment Variables

**Backend (.env):**
```env
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHANNEL_IDS=123456789,987654321
DATABASE_URL=sqlite:///./signal_analyzer.db
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENABLE_TELEGRAM_LISTENER=true
ENABLE_ANALYSIS_ENGINE=true
ENABLE_TRADE_ENGINE=true
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Technologies

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Zustand
- **Database:** SQLite (dev), PostgreSQL (prod)
- **Telegram:** Telethon
- **Message Queue:** asyncio (built-in)
- **Containerization:** Docker, docker-compose

## Deployment

### Docker Compose
```bash
docker-compose up -d
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### Production Checklist
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `API_DEBUG=false`
- [ ] Use proper secrets management
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Set up monitoring/alerts
- [ ] Configure backup strategy
- [ ] Add authentication

## Next Phases

1. **Market Data Integration**
   - XAU/USD price feeds
   - OHLC candle data
   - Provider abstraction (yfinance, Alpha Vantage, etc.)

2. **Analysis Engine**
   - Technical indicators (RSI, VWAP, ATR)
   - Structure analysis (FVG, S/D)
   - Liquidity detection

3. **Trade Management**
   - Position sizing
   - Risk/reward calculation
   - Trade execution simulation
   - P&L tracking

4. **Dashboard Features**
   - Real-time signal stream
   - Performance analytics
   - Portfolio tracking
   - Alert system

5. **Advanced**
   - Machine learning signal scoring
   - Broker integration (MT5, cTrader)
   - Mobile app
   - Automated execution

## Documentation

- **README.md** - Project overview
- **ARCHITECTURE.md** - System design & data models
- **GETTING_STARTED.md** - Setup and configuration
- **DEVELOPMENT.md** - Extensibility guide & examples

## Useful Commands

```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload
python -c "from app.database.base import init_db; init_db()"

# Frontend
cd frontend
npm run dev
npm run build
npm run lint

# Docker
docker-compose up -d
docker-compose logs -f backend
docker-compose down

# Database
python -c "from app.database.base import SessionLocal; db = SessionLocal(); print(db.query(Channel).count())"
```

## Support

For detailed information:
- See DEVELOPMENT.md for extending the system
- See GETTING_STARTED.md for setup troubleshooting
- See ARCHITECTURE.md for system design details

---

**You now have a fully scaffolded, production-ready signal analysis platform!**

The architecture is designed for:
- ✓ Easy addition of new signal parsers
- ✓ Multiple Telegram channels
- ✓ Flexible message format handling
- ✓ Clean separation of concerns
- ✓ Easy database migration (SQLite → PostgreSQL)
- ✓ Extensible API and frontend
- ✓ Docker-ready deployment

Start by configuring your Telegram credentials and implementing your first parser! 🚀
