# Getting Started

This guide will help you set up and run the Signal Analyzer application.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Telegram account with API credentials
- Git

## Backend Setup

### 1. Environment Configuration

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your settings:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone
TELEGRAM_CHANNEL_IDS=123456789,987654321
DATABASE_URL=sqlite:///./signal_analyzer.db
API_HOST=0.0.0.0
API_PORT=8000
```

### 2. Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python -c "from app.database.base import init_db; init_db()"
```

### 4. Run Backend

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API docs: `http://localhost:8000/docs`

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Variables

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

Open `http://localhost:3000` in your browser.

## Docker Deployment

### Build and Run

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Adding New Signal Parsers

### 1. Create Parser Class

Create a file in `backend/app/parsers/implementations/` that extends `SignalParser`:

```python
from app.parsers.base import SignalParser, NormalizedSignal

class MyParser(SignalParser):
    def __init__(self):
        super().__init__("my_parser_v1")
    
    def can_parse(self, message: str) -> bool:
        # Check if message matches your format
        return "MY_SIGNAL" in message
    
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        # Extract data from message
        return NormalizedSignal(
            symbol="XAUUSD",
            direction="BUY",
            order_type="LIMIT",
            entries=[4288],
            stop_loss=4273,
            take_profits=[4335]
        )
```

### 2. Register Parser

In `backend/app/parsers/implementations/__init__.py`:

```python
from app.parsers.registry import register_parser
from app.parsers.implementations.my_parser import MyParser

def init_parsers():
    register_parser("my_parser_v1", MyParser())
```

### 3. Add Message Type

Use the API or database to create a new `SignalMessageType`:

```json
{
  "name": "my_custom_signal",
  "parser_name": "my_parser_v1",
  "enabled": true,
  "description": "My custom signal format"
}
```

## API Endpoints

### Signals
- `GET /api/signals` - Get latest signals
- `GET /api/signals/{id}` - Get signal details
- `GET /api/signals/channel/{channel_id}` - Get signals from channel

### Channels
- `GET /api/channels` - List all channels
- `GET /api/channels/{id}` - Get channel details

### Message Types
- `GET /api/message-types` - List all message types
- `POST /api/message-types` - Create new message type
- `PUT /api/message-types/{id}` - Update message type
- `DELETE /api/message-types/{id}` - Delete message type

## Database Schema

### Key Tables

**channels**: Telegram channels being monitored
- id, chat_id, name, username, enabled, created_at

**signal_message_types**: Configurable signal formats
- id, name, parser_name, enabled, configuration_json, created_at, updated_at

**raw_messages**: Raw Telegram messages
- id, channel_id, message_id, text, received_at, created_at

**signals**: Parsed signals
- id, raw_message_id, channel_id, message_type_id, normalized_json, symbol, direction, order_type, stop_loss, created_at

**signal_entries**: Entry prices (multiple per signal for scaling)
- id, signal_id, price, sequence, created_at

**signal_take_profits**: Take profit targets
- id, signal_id, price, sequence, created_at

## Development Tips

### Testing Parsers

```python
import asyncio
from app.parsers.implementations.examples import GoldBuyLimitParser

parser = GoldBuyLimitParser()
message = """Buy limit GOLD
Entry: 4288
SL: 4273
TP: 4335"""

signal = asyncio.run(parser.parse(message))
print(signal)
```

### Database Queries

```python
from app.database.base import SessionLocal
from app.database.models import Signal

db = SessionLocal()
signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(10).all()
for signal in signals:
    print(signal.symbol, signal.direction, signal.entries)
db.close()
```

## Next Steps

1. Configure your Telegram credentials in `.env`
2. Add your channel IDs
3. Create signal message types in the database
4. Implement parsers for your specific message formats
5. Run the application and monitor for signals
6. Customize the dashboard as needed

## Troubleshooting

### Telegram Connection Issues

- Verify API ID and API Hash from https://my.telegram.org
- Ensure phone number includes country code
- Check channel IDs are correct

### Parser Issues

- Ensure regex patterns match your message format exactly
- Use `/api/signals` endpoint to verify parsed signals
- Check application logs for parsing errors

### Database Issues

- Delete `signal_analyzer.db` to reset database
- Check file permissions in the data directory
- Verify SQLAlchemy models match your schema
