"""
API routes for signal management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.database.models import Signal, Channel
from app.api.schemas import SignalSchema, SignalUpdateSchema, signal_to_schema
from app.services.signal_service import SignalService
from app.api.routes.telegram_auth import require_local_request
from app.telegram.listener import get_telegram_listener
from app.telegram.publisher import publish_signal, delete_published_messages

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.delete("", dependencies=[Depends(require_local_request)])
async def delete_all_signals(confirm: bool = Query(False), delete_published: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(400, "Deleting all signals requires confirm=true")
    if delete_published:
        await remove_chat_messages(db.query(Signal).all(), db)
    return {"deleted": SignalService.delete_signals(db)}


@router.delete("/{signal_id}", dependencies=[Depends(require_local_request)])
async def delete_signal(signal_id: int, delete_published: bool = Query(False), db: Session = Depends(get_db)):
    if delete_published:
        signal = db.get(Signal, signal_id)
        if signal is None:
            raise HTTPException(404, "Signal not found")
        await remove_chat_messages([signal], db)
    deleted = SignalService.delete_signals(db, signal_id)
    if not deleted:
        raise HTTPException(404, "Signal not found")
    return {"deleted": deleted}


async def remove_chat_messages(signals: list[Signal], db: Session):
    try:
        await delete_published_messages(signals, db, get_telegram_listener().client)
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception:
        db.rollback()
        raise HTTPException(502, "Telegram deletion was not confirmed. Local signals were retained; check the chat before retrying.")


@router.post("/{signal_id}/publish", dependencies=[Depends(require_local_request)])
async def publish_signal_manually(signal_id: int, confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(400, "Sending to Telegram requires confirm=true")
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(404, "Signal not found")
    try:
        status = await publish_signal(signal, db, get_telegram_listener().client, manual=True)
    except Exception:
        db.rollback()
        raise HTTPException(502, "Telegram publication was not confirmed; check the chat before retrying")
    if status == "invalid":
        raise HTTPException(422, "Signal or source fields are incomplete, invalid, or ambiguous")
    if status in ("already_recorded", "skipped"):
        raise HTTPException(409, "Signal already has a publication record or is not eligible to publish")
    if status != "sent":
        raise HTTPException(502, f"Telegram publication status: {status}. Check the chat and account permissions.")
    from app.config import settings
    return {"status": status, "destination_chat_id": str(settings.telegram_publish_chat_id_for(signal.channel.category))}


@router.post("/{signal_id}", response_model=SignalSchema, dependencies=[Depends(require_local_request)])
async def update_signal(signal_id: int, data: SignalUpdateSchema, db: Session = Depends(get_db)):
    try:
        signal = SignalService.update_signal(db, signal_id, data.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(422, str(error))
    if signal is None:
        raise HTTPException(404, "Signal not found")
    return signal_to_schema(signal)


@router.get("", response_model=list[SignalSchema])
async def get_signals(
    symbol: str = Query(None),
    category: str = Query("cfds", pattern="^(crypto|cfds)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get latest signals with optional filtering"""
    signals = SignalService.get_latest_signals(db, symbol=symbol, category=category, limit=limit)
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
