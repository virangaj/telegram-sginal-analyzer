from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.telegram_auth import require_local_request
from app.api.schemas import ReviewMessageSchema
from app.database.base import get_db
from app.database.models import Channel, Message, ParseStatus


router = APIRouter(
    prefix="/api/messages",
    tags=["messages"],
    dependencies=[Depends(require_local_request)],
)


@router.get("/review", response_model=list[ReviewMessageSchema])
def get_review_messages(
    category: Literal["crypto", "cfds"] = Query("crypto"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    messages = (
        db.query(Message)
        .join(Channel)
        .filter(Message.parse_status == ParseStatus.REVIEW, Channel.category == category)
        .order_by(Message.received_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ReviewMessageSchema(
            id=message.id,
            channel_id=message.channel_id,
            channel_name=message.channel.channel_name,
            category=message.channel.category,
            raw_text=message.raw_text,
            parse_error=message.parse_error,
            received_at=message.received_at,
        )
        for message in messages
    ]