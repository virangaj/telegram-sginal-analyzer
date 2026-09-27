# Detailed Architecture

## Core Design Principle: Configurable Signal Parsers

The application is built around the concept of **signal parser plugins**. Each Telegram channel can send signals in a different format. Instead of hard-coding logic for each format, we:

1. Store signal message types in the database
2. Each message type has an associated parser
3. Parsers normalize all formats to a common internal structure
4. The rest of the system works with the normalized format only

### Signal Message Type Configuration

**Table: `signal_message_types`**

```sql
CREATE TABLE signal_message_types (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  parser_name TEXT NOT NULL,
  enabled BOOLEAN DEFAULT true,
  configuration_json TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example entries:**

```json
[
  {
    "name": "gold_buy_limit",
    "parser_name": "gold_buy_limit_v1",
    "enabled": true,
    "configuration_json": "{}"
  },
  {
    "name": "gold_sell",
    "parser_name": "gold_sell_v1",
    "enabled": true,
    "configuration_json": "{}"
  },
  {
    "name": "gold_scaling_sell",
    "parser_name": "gold_scaling_sell_v1",
    "enabled": true,
    "configuration_json": "{}"
  }
]
```

## Normalized Signal Format

All parsers convert their input to this standard format:

```python
class NormalizedSignal(BaseModel):
    """Internal representation of any trading signal"""
    symbol: str  # e.g., "XAUUSD"
    direction: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT", "MARKET"]
    
    # Can have multiple entries (for scaling)
    entries: List[float]
    
    # Single stop loss
    stop_loss: float
    
    # Can have multiple take profits (for scaling)
    take_profits: List[float]
    
    # Metadata
    timeframe: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
```

## Parser Architecture

### Base Parser Class

```python
class SignalParser(ABC):
    @abstractmethod
    def can_parse(self, message: str) -> bool:
        """Check if this parser can handle the message"""
        pass
    
    @abstractmethod
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Convert message to normalized format"""
        pass
```

### Parser Registry

```python
class ParserRegistry:
    """Central registry of all available parsers"""
    
    def register(self, name: str, parser: SignalParser):
        """Register a new parser"""
        pass
    
    def get(self, name: str) -> SignalParser:
        """Get a parser by name"""
        pass
    
    async def parse_message(self, message: str, 
                          message_type: SignalMessageType) -> NormalizedSignal:
        """Parse using registered parser for this message type"""
        pass
```

## Implementation Examples

### Example 1: Buy Limit Parser

Input:
```
Buy limit GOLD
Entry: 4288
SL: 4273
TP: 4335
```

Parser logic:
```python
class GoldBuyLimitParser(SignalParser):
    async def parse(self, message: str) -> NormalizedSignal:
        # Extract entry, SL, TP from message
        entry = extract_number("Entry:", message)
        sl = extract_number("SL:", message)
        tp = extract_number("TP:", message)
        
        return NormalizedSignal(
            symbol="XAUUSD",
            direction="BUY",
            order_type="LIMIT",
            entries=[entry],
            stop_loss=sl,
            take_profits=[tp]
        )
```

Output:
```json
{
  "symbol": "XAUUSD",
  "direction": "BUY",
  "order_type": "LIMIT",
  "entries": [4288],
  "stop_loss": 4273,
  "take_profits": [4335]
}
```

### Example 2: Multiple Entry Parser

Input:
```
Entry: 4335
SL: 4322
TP: 4373

Entry: 4350
SL: 4322
TP: 4373
```

Parser logic:
```python
class MultiEntryParser(SignalParser):
    async def parse(self, message: str) -> NormalizedSignal:
        entries = extract_all_numbers("Entry:", message)
        sl = extract_number("SL:", message)
        tps = extract_all_numbers("TP:", message)
        
        return NormalizedSignal(
            symbol="XAUUSD",
            direction="BUY",  # inferred from context
            order_type="LIMIT",
            entries=entries,
            stop_loss=sl,
            take_profits=tps
        )
```

Output:
```json
{
  "symbol": "XAUUSD",
  "direction": "BUY",
  "order_type": "LIMIT",
  "entries": [4335, 4350],
  "stop_loss": 4322,
  "take_profits": [4373]
}
```

### Example 3: Market Sell with Scaling

Input:
```
GOLD SELL 4316.6
MORE SELL 4326.6

TP : 4301.6
TP : 4286.6
TP : 4266.6

SL : 4330.6
```

Parser logic:
```python
class GoldScalingSellParser(SignalParser):
    async def parse(self, message: str) -> NormalizedSignal:
        entries = extract_all_prices(message)
        tps = extract_all_numbers("TP:", message)
        sl = extract_number("SL:", message)
        
        return NormalizedSignal(
            symbol="XAUUSD",
            direction="SELL",
            order_type="MARKET",
            entries=entries,
            stop_loss=sl,
            take_profits=tps
        )
```

Output:
```json
{
  "symbol": "XAUUSD",
  "direction": "SELL",
  "order_type": "MARKET",
  "entries": [4316.6, 4326.6],
  "stop_loss": 4330.6,
  "take_profits": [4301.6, 4286.6, 4266.6]
}
```

## Data Model

### Tables

1. **channels** - Telegram channels to monitor
   - id, chat_id, name, username, enabled, created_at

2. **signal_message_types** - Configurable signal formats
   - id, name, description, parser_name, enabled, configuration_json, created_at, updated_at

3. **raw_messages** - Raw Telegram messages
   - id, channel_id, message_id, text, received_at, created_at

4. **signals** - Parsed and normalized signals
   - id, raw_message_id, channel_id, message_type_id, normalized_json, symbol, direction, order_type, created_at

5. **signal_entries** - Entry prices for a signal
   - id, signal_id, price, sequence, created_at

6. **signal_take_profits** - Take profit targets
   - id, signal_id, price, sequence, created_at

7. **analyses** - Technical analysis results
   - id, signal_id, timeframe, analysis_json, created_at

8. **trades** - Executed trades
   - id, signal_id, status, entry_price, current_price, pnl, created_at

## Message Flow

1. **Telegram Listener** → receives message from channel
2. **Message Processor** → stores raw message, identifies message type
3. **Parser Selection** → looks up parser from signal_message_types
4. **Signal Parsing** → converts to NormalizedSignal
5. **Storage** → saves to signals table
6. **Analysis Engine** → performs technical analysis
7. **Trade Engine** → generates trade setups
8. **API** → serves data to frontend
9. **Dashboard** → displays to user

## Extensibility Points

1. **New Signal Parser**: Create class → register in registry
2. **New Analysis Type**: Add to analysis engine
3. **New Market Data Provider**: Implement provider interface
4. **New Market Timeframe**: Add to analysis configuration
5. **New Trade Logic**: Extend trade engine

## Future Enhancements

- [ ] Machine learning for signal quality scoring
- [ ] Automated trade execution
- [ ] Real-time portfolio tracking
- [ ] Performance analytics
- [ ] Multi-user support with permissions
- [ ] Signal provider management dashboard
- [ ] Custom alert system
- [ ] Integration with brokers (MT5, cTrader, etc.)

## Database Migration Strategy

Phase 1: SQLite (current)
Phase 2: PostgreSQL (production ready)
Phase 3: Add read replicas for analytics
Phase 4: Time-series database for OHLC data

Migration approach: No business logic changes required—only swap the ORM connection string.
