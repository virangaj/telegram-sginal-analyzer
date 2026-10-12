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

Each channel is assigned a `crypto` or `cfds` category when enabled. Existing channels
are migrated to `cfds` without changing their enabled state; choose Crypto or CFDs in the
category prompt when enabling a channel. Parsed signals inherit the source channel category.
The dashboard has separate Crypto and CFDs tabs and filters signals by that stored source
category. Crypto parsing currently recognizes an explicit allowlist of common USD, USDT,
and USDC pairs; unknown tickers and ambiguous/incomplete messages remain unparsed.
Ingestion uses only parsers matching the source channel category: Crypto messages do not
fall back to gold parsing, and CFDs messages do not fall back to crypto parsing. Opposite-market
messages remain stored without a finalized signal. Existing signals are not changed by this rule.

Separate technical-analysis pipelines are not implemented yet. The current analysis modules
are standalone helpers/placeholders, not an automatically running Crypto or CFDs analysis
service. `ENABLE_ANALYSIS_ENGINE` alone does not start analysis. CFD/FX pip assumptions must
not be applied to crypto; market-specific feeds, units, and evaluation policies are still needed.

### Database

SQLite is used for development. On first run, migrations will initialize the schema.

### Automatic Telegram Publication

Recognizable forex/CFD and crypto signal messages are automatically forwarded as their
original raw text using the connected Telegram account, including incomplete crypto messages
marked REVIEW. CFDs/forex messages go to the forex destination; crypto messages go to the
crypto destination. The account must be a member with permission to post in both groups.
Raw forwarding does not infer missing levels, evaluate profitability, or execute trades.

```text
GOLD
BUY
Entry: 2000
TP1: 2020
TP2: 2030
SL: 1990
```

LIMIT/STOP orders keep their order type on the direction line. Multiple entries and targets
retain their supplied values and precision. Incomplete or wrong-side levels are not sent.
The original message must explicitly identify the instrument and direction; assumed or
ambiguous BUY/SELL values are not published.
Existing signals, historical reprocessing, and manual edits are not automatically published.
The destination is excluded from signal ingestion while automatic publication is enabled.

Configuration defaults to the approved destination; disable sending when needed:

```dotenv
TELEGRAM_AUTO_PUBLISH=true
TELEGRAM_PUBLISH_FOREX_CHAT_ID=-1004302136634
TELEGRAM_PUBLISH_CRYPTO_CHAT_ID=-5349907572
```

`TELEGRAM_PUBLISH_CHAT_ID` remains a backward-compatible alias for the forex destination.
Messages from either destination are excluded from ingestion to prevent feedback loops.

The additive `telegram_publications` ledger records each account/source-message/destination
combination and a Telegram random ID before sending. Duplicate attempts are suppressed,
including after restart or signal deletion. Failed/unknown/sending records are not blindly
retried; inspect destination history before any recovery to avoid duplicate public posts.
Delivery is not guaranteed: permission errors, outages, or a process interruption can require
manual reconciliation. Telegram delivery failures do not turn a parsed signal into a parse failure.

Current startup initialization creates the new ledger table without altering existing tables.
For a controlled SQLite rollout, the same additive schema is provided in
[001_telegram_publications.sql](backend/app/database/migrations/001_telegram_publications.sql).
Back up the database before applying schema changes. This standalone script is not a
configured Alembic baseline and does not migrate existing signal/message columns.

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
Signals appear in a table with entry, SL, labeled TPs, per-target planned R:R, stored
status, and source channel. Planned R:R uses the average listed entry, not observed fills.
Success/Failed labels are shown only when supplied by the backend; pending or completed
states are not automatically interpreted as profitable or losing outcomes.
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

### Biquote Market Quotes

The dashboard displays XAU/USD bid, ask, and midpoint quotes from
[Biquote](https://biquote.io/guides/free-forex-api-python.html) using the anonymous REST
batch endpoint. No API key or additional dependency is required. The browser requests
`GET /api/market/XAUUSD` every second; a shared backend cache limits upstream refreshes.
The displayed provider/broker source, quote timestamp, age, and market-state label come
from validated provider data. A closed/stale quote is shown as a last quote, not live.

Optional backend environment settings:

```dotenv
BIQUOTE_BASE_URL=https://biquote.io
BIQUOTE_POLL_INTERVAL_SECONDS=1
BIQUOTE_STALE_AFTER_SECONDS=300
BIQUOTE_SYMBOLS=XAUUSD,XAGUSD,EURUSD,GBPUSD,USDJPY
```

These provider-specific settings are independent of the older `MARKET_DATA_*` placeholders.
`GET /api/market/{symbol}` supports configured symbols and returns explicit unavailable,
unknown, stale, closed, or live status. Rate limits/outages cause bounded backoff; failures
preserve the last source timestamp and never make stale data appear fresh.
This integration supplies quotes only: it does not persist candles, implement historical
replay, subscribe to SignalR, generate trading signals, or place orders. The provider's
OHLC documentation describes mixed upstream sources; historical integration needs explicit
per-series provenance and coverage before those bars can be used as replay evidence.

See `.env.example` for required environment variables:
- Telegram API credentials
- Database connection
- Market data provider settings
- API configuration

## Signal Format Normalization

Selected Telegram channels accept both incoming messages and messages sent by the connected
account. The automatic-publication destination remains excluded to prevent feedback loops.
The listener handles new messages only; messages skipped before this change are not
automatically imported from Telegram history.

The default gold parser accepts explicit GOLD/XAUUSD/XAU/USD BUY or SELL signals with
complete entry, SL, and TP values, including numbered targets and scaling entries:

```text
GOLD BUY 2000
MORE BUY 1995
TP1: 2020
TP2: 2030
SL: 1980
```

Labeled `Entry:` values and explicit MARKET/LIMIT/STOP orders are also supported.
Missing levels, conflicting directions, wrong-side prices, follow-up/result messages, and
entry ranges such as `2000-2010` remain unparsed for review rather than being guessed.
Legacy configured parser names resolve to the same validated gold parser.

Crypto channels additionally recognize LONG/SHORT as BUY/SELL, markdown/Unicode-bold
labels, emoji prefixes, and absolute entry/target/SL prices on the same or next line.
Labeled price sections also accept multiline lists, including `1) 120` and `1. 120`,
preserving every supplied price in source order without treating list numbers as prices.
For example, `BTC/USDT`, `FUTURE (SHORT)`, `Enter Price: 85500`,
`Target: 77000 (+100%)`, and `SL: 94000 (-100%)` produce a SELL signal using the explicit
85500/77000/94000 prices, not the annotated percentages. BTW, PNUT, and CHIP are included
in the recognized ticker set; the quote currency must still be explicitly supplied.

Recognized but incomplete crypto messages are preserved with parsing status REVIEW and
a specific reason. Percentage-only targets (including leveraged-return ambiguity), entry
ranges, unspecified current-market entries, and missing quote currencies/SL/TP are not
converted into invented levels. REVIEW messages do not appear in the finalized-signal table;
recognizable source messages are forwarded verbatim to the configured crypto destination.
Original text, leverage notes, and all supplied values remain in the raw message for review.

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
