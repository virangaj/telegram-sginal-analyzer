# Development Guide

This guide explains how to extend and work with the Signal Analyzer application.

## Architecture Overview

The Signal Analyzer is built on a **plugin-based architecture** where signal formats are completely decoupled from business logic:

1. **Message Reception**: Raw Telegram messages arrive via Telethon
2. **Parser Selection**: System identifies which parser handles the message
3. **Normalization**: Parser converts to standard `NormalizedSignal` format
4. **Persistence**: Normalized signal stored in database
5. **Downstream Processing**: All logic works with normalized format

This means you can add new signal providers without touching core code.

## Parser Development

### Understanding the Parser Interface

```python
class SignalParser(ABC):
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def can_parse(self, message: str) -> bool:
        """Returns True if parser can handle message format"""
        pass
    
    @abstractmethod
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Converts raw message to NormalizedSignal"""
        pass
```

### Creating a Parser

**Step 1: Create the parser file**

`backend/app/parsers/implementations/forex_parser.py`:

```python
from app.parsers.base import SignalParser, NormalizedSignal
from typing import Optional
import re


class ForexSignalParser(SignalParser):
    """Parses EURUSD signals from provider XYZ"""
    
    def __init__(self):
        super().__init__("forex_xyz_v1")
    
    def can_parse(self, message: str) -> bool:
        """Check if message is EURUSD signal"""
        return "EURUSD" in message and "BUY" in message.upper() or "SELL" in message.upper()
    
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Extract signal from message"""
        try:
            # Parse your specific format
            symbol = self._extract_symbol(message)
            direction = self._extract_direction(message)
            entry = self._extract_number(message, r"Entry:\s*([\d.]+)")
            sl = self._extract_number(message, r"SL:\s*([\d.]+)")
            tp = self._extract_number(message, r"TP:\s*([\d.]+)")
            
            if not all([symbol, direction, entry, sl, tp]):
                return None
            
            return NormalizedSignal(
                symbol=symbol,
                direction=direction,
                order_type="LIMIT",
                entries=[entry],
                stop_loss=sl,
                take_profits=[tp],
                provider="forex_xyz",
                confidence=0.95
            )
        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            return None
    
    @staticmethod
    def _extract_symbol(message: str) -> str:
        match = re.search(r"(EUR|GBP|USD|JPY)\w{3}", message)
        return match.group(0) if match else None
    
    @staticmethod
    def _extract_direction(message: str) -> str:
        if "BUY" in message.upper():
            return "BUY"
        elif "SELL" in message.upper():
            return "SELL"
        return None
    
    @staticmethod
    def _extract_number(text: str, pattern: str) -> Optional[float]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
```

**Step 2: Register the parser**

Edit `backend/app/parsers/implementations/__init__.py`:

```python
from app.parsers.registry import register_parser
from app.parsers.implementations.examples import (
    GoldBuyLimitParser,
    GoldScalingSellParser,
    MultiEntryParser
)
from app.parsers.implementations.forex_parser import ForexSignalParser  # NEW


def init_parsers():
    """Initialize and register all available parsers"""
    
    # Existing parsers
    register_parser("gold_buy_limit_v1", GoldBuyLimitParser())
    register_parser("gold_scaling_sell_v1", GoldScalingSellParser())
    register_parser("multi_entry_v1", MultiEntryParser())
    
    # New parser
    register_parser("forex_xyz_v1", ForexSignalParser())
```

**Step 3: Create message type in database**

```python
from app.database.base import SessionLocal
from app.database.models import SignalMessageType

db = SessionLocal()
msg_type = SignalMessageType(
    name="forex_xyz_signal",
    description="EURUSD signals from XYZ provider",
    parser_name="forex_xyz_v1",
    enabled=True
)
db.add(msg_type)
db.commit()
db.close()
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/message-types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "forex_xyz_signal",
    "parser_name": "forex_xyz_v1",
    "enabled": true,
    "description": "EURUSD signals from XYZ provider"
  }'
```

### Best Practices for Parsers

1. **Robust Extraction**
   ```python
   # ✓ Good: Handle missing fields
   def can_parse(self, message: str) -> bool:
       return "SIGNAL" in message and any(
           symbol in message for symbol in ["XAUUSD", "EURUSD"]
       )
   
   # ✗ Bad: Assumes all fields present
   def can_parse(self, message: str) -> bool:
       return message.startswith("SIGNAL")
   ```

2. **Validation**
   ```python
   # ✓ Good: Validate extracted values
   if sl >= entry or tp <= entry:
       return None  # Invalid setup
   
   # ✗ Bad: No validation
   return NormalizedSignal(entries=entry, stop_loss=sl, take_profits=tp)
   ```

3. **Error Handling**
   ```python
   # ✓ Good: Graceful failure
   try:
       entry = float(match.group(1))
   except (ValueError, IndexError):
       return None
   
   # ✗ Bad: Unhandled exception
   entry = float(match.group(1))
   ```

4. **Documentation**
   ```python
   class MyParser(SignalParser):
       """
       Parses signals in format:
       
       BUY GOLD
       Entry: 4288
       SL: 4273
       TP: 4335
       """
   ```

## Adding API Endpoints

### New Signals Endpoint

`backend/app/api/routes/stats.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database.base import get_db
from app.database.models import Signal

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/daily")
async def get_daily_stats(db: Session = Depends(get_db)):
    """Get signal statistics for today"""
    today = datetime.utcnow().date()
    
    signals_today = db.query(Signal).filter(
        func.date(Signal.created_at) == today
    ).count()
    
    return {
        "date": today,
        "signals_count": signals_today,
        "by_symbol": get_signals_by_symbol(db, today),
        "by_direction": get_signals_by_direction(db, today)
    }


def get_signals_by_symbol(db, date):
    results = db.query(
        Signal.symbol,
        func.count(Signal.id)
    ).filter(func.date(Signal.created_at) == date).group_by(Signal.symbol).all()
    
    return {symbol: count for symbol, count in results}


def get_signals_by_direction(db, date):
    results = db.query(
        Signal.direction,
        func.count(Signal.id)
    ).filter(func.date(Signal.created_at) == date).group_by(Signal.direction).all()
    
    return {direction: count for direction, count in results}
```

Register in `app/main.py`:

```python
from app.api.routes import signals, channels, message_types, stats

# ...
app.include_router(stats.router)
```

## Database Migrations

### Adding a New Column

```python
# 1. Update model
class Signal(Base):
    __tablename__ = "signals"
    # ... existing fields
    confidence: float = Column(Float, nullable=True)  # NEW

# 2. Create migration
# python -m alembic revision --autogenerate -m "Add confidence to signals"

# 3. Apply migration
# python -m alembic upgrade head
```

### Adding a New Table

```python
# 1. Define model
class SignalAlert(Base):
    __tablename__ = "signal_alerts"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    alert_type = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)

# 2. Create and apply migration
# python -m alembic revision --autogenerate -m "Create signal_alerts table"
# python -m alembic upgrade head
```

## Frontend Development

### Adding a New Page

`frontend/pages/analysis.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import { Layout } from '@/components/Layout';
import { apiClient } from '@/lib/api';
import { Signal } from '@/lib/types';

export default function AnalysisPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAnalysis = async () => {
      try {
        const response = await apiClient.getSignals();
        setSignals(response.data);
      } catch (error) {
        console.error('Failed to load signals', error);
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, []);

  return (
    <Layout title="Analysis - Signal Analyzer">
      <div className="space-y-8">
        <h2 className="text-3xl font-bold text-white">Signal Analysis</h2>
        
        {loading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="grid gap-4">
            {signals.map(signal => (
              <div key={signal.id} className="p-4 bg-slate-800 rounded">
                <h3 className="font-bold text-white">{signal.symbol}</h3>
                <p className="text-slate-400">{signal.direction} {signal.order_type}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
```

### Adding a New Component

`frontend/components/SignalChart.tsx`:

```typescript
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Signal } from '@/lib/types';

interface SignalChartProps {
  signals: Signal[];
}

export const SignalChart: React.FC<SignalChartProps> = ({ signals }) => {
  const data = signals.map(signal => ({
    date: new Date(signal.created_at).toLocaleDateString(),
    count: 1
  }));

  return (
    <LineChart width={800} height={400} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="date" />
      <YAxis />
      <Tooltip />
      <Line type="monotone" dataKey="count" stroke="#8884d8" />
    </LineChart>
  );
};
```

## Testing Locally

### Test a Parser

```python
import asyncio
from app.parsers.implementations.examples import GoldBuyLimitParser

async def test_parser():
    parser = GoldBuyLimitParser()
    
    message = """Buy limit GOLD
Entry: 4288
SL: 4273
TP: 4335"""
    
    signal = await parser.parse(message)
    print(signal.model_dump_json(indent=2))

asyncio.run(test_parser())
```

### Test Database Queries

```python
from app.database.base import SessionLocal
from app.database.models import Signal

db = SessionLocal()

# Get latest signals
signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(5).all()
for signal in signals:
    print(f"{signal.symbol} {signal.direction} - {len(signal.entries)} entries")

# Get statistics
from sqlalchemy import func
stats = db.query(
    Signal.symbol,
    Signal.direction,
    func.count(Signal.id).label("count")
).group_by(Signal.symbol, Signal.direction).all()

for symbol, direction, count in stats:
    print(f"{symbol} {direction}: {count} signals")

db.close()
```

### Test API Endpoints

```bash
# Get signals
curl http://localhost:8000/api/signals

# Get specific signal
curl http://localhost:8000/api/signals/1

# Create message type
curl -X POST http://localhost:8000/api/message-types \
  -H "Content-Type: application/json" \
  -d '{"name":"test","parser_name":"gold_buy_limit_v1","enabled":true}'

# Get message types
curl http://localhost:8000/api/message-types
```

## Performance Optimization

### Database Indexing

```python
class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)  # Frequently filtered
    created_at = Column(DateTime, index=True)  # Frequently sorted
    channel_id = Column(Integer, index=True)  # Foreign key lookups
```

### Query Optimization

```python
# ✓ Good: Use eager loading
signals = db.query(Signal).options(
    joinedload(Signal.entries),
    joinedload(Signal.take_profits)
).limit(10).all()

# ✗ Bad: Lazy loading causes N+1 queries
signals = db.query(Signal).limit(10).all()
for signal in signals:
    print(len(signal.entries))  # Query per signal!
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_parser_config(message_type_id: int):
    db = SessionLocal()
    config = db.query(SignalMessageType).filter(
        SignalMessageType.id == message_type_id
    ).first()
    db.close()
    return config
```

## Deployment

### Environment-Specific Configuration

`backend/.env.production`:

```env
DATABASE_URL=postgresql://user:password@prod-db.example.com/signal_analyzer
API_DEBUG=false
LOG_LEVEL=INFO
ENABLE_TELEGRAM_LISTENER=true
```

### Running in Production

```bash
# With gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# With Docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Debugging

### Enable Debug Logging

```python
# In config.py
LOG_LEVEL=DEBUG
```

### Add Debug Statements

```python
import logging

logger = logging.getLogger(__name__)

async def parse(self, message: str):
    logger.debug(f"Attempting to parse: {message[:100]}")
    
    entry = self._extract_number(message, r"Entry:\s*([\d.]+)")
    logger.debug(f"Extracted entry: {entry}")
    
    if entry is None:
        logger.warning(f"Failed to extract entry from: {message}")
        return None
    
    logger.info(f"Successfully parsed signal for {signal.symbol}")
    return signal
```

### Database Inspection

```python
# Check all channels
from app.database.models import Channel
db = SessionLocal()
channels = db.query(Channel).all()
print(f"Found {len(channels)} channels")
for ch in channels:
    print(f"  {ch.chat_id}: {ch.name}")
```

## Troubleshooting Common Issues

### Parser Not Detecting Messages

```python
# Debug: Check can_parse logic
parser = MyParser()
message = "... your message ..."
print(f"can_parse: {parser.can_parse(message)}")  # Should be True

# Debug: Check parse output
signal = asyncio.run(parser.parse(message))
print(signal)  # Should not be None
```

### Missing Database Records

```python
# Check raw_messages table
from app.database.models import RawMessage
db = SessionLocal()
messages = db.query(RawMessage).all()
print(f"Total raw messages: {len(messages)}")

# Check for parse errors in logs
grep "Error parsing signal" logs/*.log
```

### Frontend Not Connecting to Backend

1. Check API URL in `.env.local`
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check browser console for CORS errors
4. Ensure port 8000 is accessible

## Next Steps

- Add authentication/authorization
- Implement webhook system for alerts
- Build mobile app using React Native
- Add data export (CSV, Excel)
- Implement signal performance tracking
- Create Grafana dashboards for monitoring
