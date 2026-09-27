"""
Database models for the Signal Analyzer application
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ParseStatus(str, enum.Enum):
    """Status of message parsing"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    INVALID = "invalid"
    REVIEW = "review"  # For AI-parsed signals that need review


class SignalStatus(str, enum.Enum):
    """Status of a signal"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INVALID = "invalid"


class Channel(Base):
    """Telegram channel being monitored"""
    
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True)
    platform = Column(String, default="telegram", nullable=False)  # "telegram", "email", etc.
    external_channel_id = Column(String, nullable=False, index=True)  # "-1002422665513" for Telegram
    channel_name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    parser_type = Column(String, nullable=True)  # Can enforce specific parser
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="channel")


class SignalMessageType(Base):
    """Configurable signal message type definitions"""
    
    __tablename__ = "signal_message_types"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    parser_name = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=True, index=True)
    configuration_json = Column(Text, nullable=True)  # JSON string for parser-specific config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signals = relationship("Signal", back_populates="message_type")


class Message(Base):
    """Raw message from any source - ALWAYS STORED, parsed or not"""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    external_message_id = Column(String, nullable=False)  # Telegram message ID or equivalent
    source = Column(String, default="telegram", nullable=False)  # Source platform
    raw_text = Column(Text, nullable=False)
    
    # Parsing metadata
    parse_status = Column(SQLEnum(ParseStatus), default=ParseStatus.PENDING, nullable=False, index=True)
    parse_error = Column(Text, nullable=True)  # Error message if parsing failed
    detected_message_type_id = Column(Integer, ForeignKey("signal_message_types.id"), nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    channel = relationship("Channel", back_populates="messages")
    signal = relationship("Signal", back_populates="message", uselist=False)  # 0 or 1 signal per message
    detected_message_type = relationship("SignalMessageType", foreign_keys=[detected_message_type_id])


class Signal(Base):
    """Parsed and normalized trading signal"""
    
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, unique=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    message_type_id = Column(Integer, ForeignKey("signal_message_types.id"), nullable=True)  # Resolved from parser name; unknown if no matching configured type
    
    # Normalized data
    symbol = Column(String, nullable=False, index=True)  # "XAUUSD", "EURUSD"
    direction = Column(String, nullable=False)  # "BUY" or "SELL"
    order_type = Column(String, nullable=False)  # "LIMIT" or "MARKET"
    status = Column(SQLEnum(SignalStatus), default=SignalStatus.PENDING, nullable=False, index=True)
    
    # Pricing
    stop_loss = Column(Float, nullable=False)
    raw_signal_type = Column(String, nullable=True)  # Parser name or type
    
    # Metadata
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0 confidence score
    normalized_json = Column(Text, nullable=False)  # Full normalized signal as JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="signal")
    channel = relationship("Channel", back_populates="signals")
    message_type = relationship("SignalMessageType", back_populates="signals")
    entries = relationship("SignalEntry", back_populates="signal", cascade="all, delete-orphan")
    take_profits = relationship("SignalTakeProfit", back_populates="signal", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="signal", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="signal")


class SignalEntry(Base):
    """Entry price for a signal (supports multiple entries for scaling)"""
    
    __tablename__ = "signal_entries"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)  # Order of entry (1, 2, 3...)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="entries")


class SignalTakeProfit(Base):
    """Take profit target for a signal (supports multiple TPs for scaling)"""
    
    __tablename__ = "signal_take_profits"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)  # Order of TP (1, 2, 3...)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="take_profits")


class Analysis(Base):
    """Technical analysis results for a signal"""
    
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    timeframe = Column(String, nullable=False)  # 4H, 1H, 15M, etc.
    analysis_json = Column(Text, nullable=False)  # Full analysis as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="analyses")


class Trade(Base):
    """Executed or simulated trade based on a signal"""
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    status = Column(String, nullable=False)  # PENDING, ACTIVE, CLOSED, CANCELLED
    entry_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    trade_json = Column(Text, nullable=True)  # Additional trade details as JSON
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="trades")


class MarketCandle(Base):
    """OHLC candle storage for historical analysis/backtesting"""

    __tablename__ = "market_candles"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False, index=True)  # "4H", "1H", "15M", "5M"
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_candle_symbol_tf_ts"),
    )


class AnalysisRun(Base):
    """Records each time analysis was executed, so results can be reproduced"""

    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    market_timestamp = Column(DateTime, nullable=False)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    signal = relationship("Signal")
    market_analyses = relationship("MarketAnalysis", back_populates="analysis_run", cascade="all, delete-orphan")
    trade_setups = relationship("TradeSetup", back_populates="analysis_run")


class MarketAnalysis(Base):
    """Structured market analysis output for a signal at a point in time"""

    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)

    regime = Column(String, nullable=True)  # BULLISH, BEARISH, RANGE, TRANSITION, UNKNOWN
    structure_summary = Column(Text, nullable=True)  # JSON
    liquidity_summary = Column(Text, nullable=True)  # JSON
    supply_demand_summary = Column(Text, nullable=True)  # JSON
    fvg_summary = Column(Text, nullable=True)  # JSON
    indicator_summary = Column(Text, nullable=True)  # JSON (ATR, VWAP, RSI, etc.)
    news_summary = Column(Text, nullable=True)  # JSON

    decision = Column(String, nullable=True)  # WAIT, VALID_SETUP, INVALIDATED, NO_SETUP, ACTIVE, COMPLETED
    reasoning = Column(Text, nullable=True)  # Human-readable explanation

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    signal = relationship("Signal")
    analysis_run = relationship("AnalysisRun", back_populates="market_analyses")


class TradeSetup(Base):
    """Structured trade setup derived from signal + market analysis"""

    __tablename__ = "trade_setups"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("market_analysis.id"), nullable=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True)

    status = Column(String, nullable=False, default="WAIT", index=True)  # WAIT, VALID_SETUP, INVALIDATED, NO_SETUP, ACTIVE, COMPLETED
    direction = Column(String, nullable=False)  # BUY or SELL

    preferred_entry = Column(Float, nullable=True)
    entry_zone_low = Column(Float, nullable=True)
    entry_zone_high = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    risk_reward = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    signal = relationship("Signal")
    analysis_run = relationship("AnalysisRun", back_populates="trade_setups")
    entries = relationship("TradeSetupEntry", back_populates="trade_setup", cascade="all, delete-orphan")
    targets = relationship("TradeSetupTarget", back_populates="trade_setup", cascade="all, delete-orphan")


class TradeSetupEntry(Base):
    """Scaling entry within a trade setup"""

    __tablename__ = "trade_setup_entries"

    id = Column(Integer, primary_key=True)
    trade_setup_id = Column(Integer, ForeignKey("trade_setups.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    allocation_percent = Column(Float, nullable=False)  # 0.0 - 1.0
    sequence = Column(Integer, nullable=False)

    # Relationships
    trade_setup = relationship("TradeSetup", back_populates="entries")


class TradeSetupTarget(Base):
    """Take-profit target within a trade setup"""

    __tablename__ = "trade_setup_targets"

    id = Column(Integer, primary_key=True)
    trade_setup_id = Column(Integer, ForeignKey("trade_setups.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)

    # Relationships
    trade_setup = relationship("TradeSetup", back_populates="targets")
