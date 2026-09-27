"""
API routes for signal management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.database.models import Signal, Channel
from app.api.schemas import SignalSchema, signal_to_schema
from app.services.signal_service import SignalService

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=list[SignalSchema])
async def get_signals(
    symbol: str = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get latest signals with optional filtering"""
    signals = SignalService.get_latest_signals(db, symbol=symbol, limit=limit)
    return [signal_to_schema(s) for s in signals]


@router.get("/{signal_id}", response_model=SignalSchema)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a specific signal by ID"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal_to_schema(signal)


@router.get("/channel/{channel_id}", response_model=list[SignalSchema])
async def get_signals_by_channel(
    channel_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get signals from a specific channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    signals = db.query(Signal).filter(
        Signal.channel_id == channel_id
    ).order_by(Signal.created_at.desc()).limit(limit).all()
    
    return [signal_to_schema(s) for s in signals]
