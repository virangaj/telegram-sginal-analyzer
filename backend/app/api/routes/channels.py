"""
API routes for channel management
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.database.models import Channel
from app.api.schemas import ChannelSchema

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=list[ChannelSchema])
async def get_channels(db: Session = Depends(get_db)):
    """Get all configured channels"""
    return db.query(Channel).all()


@router.get("/{channel_id}", response_model=ChannelSchema)
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get a specific channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise ValueError("Channel not found")
    return channel
