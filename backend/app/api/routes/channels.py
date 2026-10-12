"""
API routes for channel management
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Literal
from telethon.errors import RPCError
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.database.models import Channel
from app.api.schemas import ChannelSchema
from app.api.routes.telegram_auth import require_local_request
from app.telegram.listener import get_telegram_listener

router = APIRouter(prefix="/api/channels", tags=["channels"], dependencies=[Depends(require_local_request)])


class ChannelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    category: Literal["crypto", "cfds"] | None = None


@router.get("", response_model=list[ChannelSchema])
async def get_channels(db: Session = Depends(get_db)):
    """Get all configured channels"""
    return db.query(Channel).all()


@router.post("/sync", response_model=list[ChannelSchema])
async def sync_channels(db: Session = Depends(get_db)):
    listener = get_telegram_listener()
    if not listener.client or not await listener.client.is_user_authorized():
        raise HTTPException(409, "Connect your Telegram account first")
    try:
        await listener.sync_channels(db)
    except RPCError:
        db.rollback()
        raise HTTPException(502, "Could not load Telegram channels. Try again later.")
    await listener.ensure_listening()
    return db.query(Channel).filter(Channel.platform == "telegram").order_by(Channel.channel_name).all()


@router.post("/{channel_id}", response_model=ChannelSchema)
async def select_channel(channel_id: int, data: ChannelSelection, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id, Channel.platform == "telegram").first()
    if not channel:
        raise HTTPException(404, "Channel not found")
    if data.enabled is None and data.category is None:
        raise HTTPException(422, "Provide enabled or category")
    if data.enabled is not None:
        channel.enabled = data.enabled
    if data.category is not None:
        channel.category = data.category
    db.commit()
    db.refresh(channel)
    listener = get_telegram_listener()
    listener.refresh_channels()
    await listener.ensure_listening()
    return channel


@router.get("/{channel_id}", response_model=ChannelSchema)
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get a specific channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(404, "Channel not found")
    return channel
