"""
API schemas for request/response validation
"""

from typing import Optional, List, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


PositivePrice = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class SignalUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[str] = Field(default=None, min_length=1, max_length=32)
    direction: Optional[Literal["BUY", "SELL"]] = None
    order_type: Optional[Literal["MARKET", "LIMIT", "STOP"]] = None
    entries: Optional[List[PositivePrice]] = Field(default=None, min_length=1)
    stop_loss: Optional[PositivePrice] = None
    take_profits: Optional[List[PositivePrice]] = Field(default=None, min_length=1)
    confidence: Optional[float] = Field(default=None, ge=0, le=1, allow_inf_nan=False)


class NormalizedSignalSchema(BaseModel):
    """Schema for normalized signals"""
    
    symbol: str
    direction: str
    order_type: str
    entries: List[float]
    stop_loss: float
    take_profits: List[float]
    timeframe: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None


class SignalMessageTypeSchema(BaseModel):
    """Schema for signal message types"""
    
    id: int
    name: str
    description: Optional[str]
    parser_name: str
    enabled: bool
    configuration_json: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SignalMessageTypeCreateSchema(BaseModel):
    """Schema for creating signal message types"""
    
    name: str
    description: Optional[str] = None
    parser_name: str
    enabled: bool = True
    configuration_json: Optional[str] = None


class MessageSchema(BaseModel):
    """Schema for raw messages"""
    
    id: int
    channel_id: int
    external_message_id: str
    source: str
    raw_text: str
    parse_status: str
    parse_error: Optional[str]
    detected_message_type_id: Optional[int]
    received_at: datetime
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChannelSchema(BaseModel):
    """Schema for Telegram channels"""
    
    id: int
    platform: str
    external_channel_id: str
    channel_name: str
    enabled: bool
    category: Literal["crypto", "cfds"] = "cfds"
    parser_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SignalSchema(BaseModel):
    """Schema for signals"""
    
    id: int
    message_id: int
    channel_id: int
    channel_name: Optional[str] = None
    category: Literal["crypto", "cfds"] = "cfds"
    message_type_id: Optional[int]
    symbol: str
    direction: str
    order_type: str
    entries: List[float]
    stop_loss: float
    take_profits: List[float]
    confidence: Optional[float]
    status: str
    raw_signal_type: Optional[str]
    normalized_json: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


def signal_to_schema(signal) -> "SignalSchema":
    """Build a SignalSchema from a Signal ORM instance, pulling entry/TP prices from their tables"""
    return SignalSchema(
        id=signal.id,
        message_id=signal.message_id,
        channel_id=signal.channel_id,
        channel_name=signal.channel.channel_name if signal.channel else None,
        category=signal.channel.category if signal.channel else "cfds",
        message_type_id=signal.message_type_id,
        symbol=signal.symbol,
        direction=signal.direction,
        order_type=signal.order_type,
        entries=[e.entry_price for e in sorted(signal.entries, key=lambda e: e.sequence)],
        stop_loss=signal.stop_loss,
        take_profits=[tp.price for tp in sorted(signal.take_profits, key=lambda tp: tp.sequence)],
        confidence=signal.confidence,
        status=signal.status.value if hasattr(signal.status, "value") else signal.status,
        raw_signal_type=signal.raw_signal_type,
        normalized_json=signal.normalized_json,
        created_at=signal.created_at,
        updated_at=signal.updated_at,
    )
