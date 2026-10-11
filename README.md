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

### Telegram Channels

Open `http://localhost:3000/channels` to connect Telegram and manage listening channels.
An existing authenticated Telegram session is reused. Otherwise, enter your phone
number, Telegram login code, and two-step verification password if required.

Refresh loads channels and groups from the connected account. Each checkbox saves
the channel's enabled flag in the database and updates the live listener without a
restart. Deselecting every channel pauses ingestion. Refreshing or restarting does
not reset saved choices. Newly discovered channels default to disabled, except for
IDs already configured in `TELEGRAM_CHANNEL_IDS`.

This is a local, single-Telegram-account workflow, not multi-user authentication.
Account and channel management endpoints reject non-local clients and origins.
Keep the Telegram session file private; it grants access to the connected account.
Login codes and passwords are not stored in the application database.

### Database

SQLite is used for development. On first run, migrations will initialize the schema.

### Signal Management

Local clients can manage stored signals through these endpoints:

| Operation | Endpoint | Body/Query |
|---|---|---|
| Update one signal | `POST /api/signals/{signal_id}` | Partial fields such as `{"entries": [2000], "stop_loss": 1990, "take_profits": [2020]}` |
| Delete one signal | `DELETE /api/signals/{signal_id}` | No body |
| Delete all signals | `DELETE /api/signals?confirm=true` | Explicit confirmation required |

Updates validate prices and direction, synchronize normalized JSON and price rows, retain
the previous normalized values in `manual_edits`, invalidate derived analysis/events/setups,
and reset the signal to pending. Signals with trade records cannot be edited.
Deletion removes signal-dependent analyses, events, setups, and trade records, but retains
raw messages, channels, message-type configuration, and market candles. It is permanent;
back up important records first. New Telegram messages may create new signals afterward.

Frontend helpers are `apiClient.updateSignal`, `deleteSignal`, and `deleteAllSignals`.
The dashboard exposes Edit and Delete controls on each signal and a Delete All action.
The edit dialog accepts comma-separated entry and take-profit prices plus a numeric stop
loss. Invalid prices and failed saves keep the dialog open; deletion requires confirmation.

To clear stored market data from `backend`, use:

```python
from app.database.base import clear_market_data
deleted_counts = clear_market_data()
```

This clears market candles and legacy support/resistance zones and zone-touch records,
returning deleted counts per table. It does not delete signals, raw messages, channels,
or signal-linked historical analysis. Back up the database before running it.

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
