# Signal Analyzer

A production-ready platform for analyzing trading signals from multiple Telegram channels with configurable message parsers, market data integration, and trade management.

## Architecture

```
                    ┌─────────────────────┐
                    │ Telegram Channels   │
                    │ Multiple Chat IDs    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Message Listener    │
                    │ Python              │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Signal Parser       │
                    │ Configurable Types  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ SQLite              │
                    │ Messages            │
                    │ Signals             │
                    │ Channels            │
                    │ Analyses             │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
       Market Data Service              Analysis Engine
       XAU/USD ticks                     4H / 1H / 15M
       OHLC                              Structure
                                         Liquidity
                                         FVG
                                         S/D
                                         VWAP
                                         RSI
                                         ATR
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Trade Setup Engine  │
                    │ Entry / SL / TP     │
                    │ Scaling             │
                    │ Risk                │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Next.js Dashboard   │
                    └─────────────────────┘
```

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** Next.js + TypeScript
- **Database:** SQLite (PostgreSQL for production)
- **ORM:** SQLAlchemy
- **Validation:** Pydantic
- **Background tasks:** Python asyncio
- **Telegram:** Telethon
- **Market data:** Provider abstraction

## Project Structure

```
signal-analyzer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── models.py
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── implementations/
│   │   ├── telegram/
│   │   │   ├── __init__.py
│   │   │   ├── listener.py
│   │   │   └── handlers.py
│   │   ├── market/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── providers/
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   └── engine.py
│   │   ├── trade/
│   │   │   ├── __init__.py
│   │   │   └── engine.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   └── schemas.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── signal_service.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   ├── components/
│   ├── pages/
│   ├── styles/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── docker/
│   ├── Dockerfile.backend
│   └── docker-compose.yml
├── .gitignore
├── README.md
└── ARCHITECTURE.md
```

## Key Design Decisions

1. **Configurable Signal Parsers**: All signal formats are normalized to a common internal structure. Different Telegram channels with different message formats are handled via pluggable parsers.

2. **No Hard-coded Formats**: Message types are stored in the database with associated parser logic, allowing new signal sources to be added without modifying the core application.

3. **Separation of Concerns**: 
   - Parser layer handles format conversion
   - Database layer manages persistence
   - Analysis engine handles market logic
   - API layer exposes functionality
   - Frontend provides visualization

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Telegram credentials and settings
python -m uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Database

SQLite is used for development. On first run, migrations will initialize the schema.

## Configuration

See `.env.example` for required environment variables:
- Telegram API credentials
- Database connection
- Market data provider settings
- API configuration

## Signal Format Normalization

All signals are normalized to:

```json
{
  "symbol": "XAUUSD",
  "direction": "BUY|SELL",
  "order_type": "LIMIT|MARKET",
  "entries": [4288],
  "stop_loss": 4273,
  "take_profits": [4335]
}
```

## License

Private
