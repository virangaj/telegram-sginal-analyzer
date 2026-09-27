"""
API routes for signal message type management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.database.models import SignalMessageType
from app.api.schemas import SignalMessageTypeSchema, SignalMessageTypeCreateSchema

router = APIRouter(prefix="/api/message-types", tags=["message-types"])


@router.get("", response_model=list[SignalMessageTypeSchema])
async def get_message_types(
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all signal message types"""
    query = db.query(SignalMessageType)
    if enabled_only:
        query = query.filter(SignalMessageType.enabled == True)
    return query.all()


@router.get("/{message_type_id}", response_model=SignalMessageTypeSchema)
async def get_message_type(message_type_id: int, db: Session = Depends(get_db)):
    """Get a specific message type"""
    msg_type = db.query(SignalMessageType).filter(
        SignalMessageType.id == message_type_id
    ).first()
    
    if not msg_type:
        raise HTTPException(status_code=404, detail="Message type not found")
    
    return msg_type


@router.post("", response_model=SignalMessageTypeSchema)
async def create_message_type(
    data: SignalMessageTypeCreateSchema,
    db: Session = Depends(get_db)
):
    """Create a new signal message type"""
    # Check if name already exists
    existing = db.query(SignalMessageType).filter(
        SignalMessageType.name == data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Message type name already exists")
    
    msg_type = SignalMessageType(**data.model_dump())
    db.add(msg_type)
    db.commit()
    db.refresh(msg_type)
    return msg_type


@router.put("/{message_type_id}", response_model=SignalMessageTypeSchema)
async def update_message_type(
    message_type_id: int,
    data: SignalMessageTypeCreateSchema,
    db: Session = Depends(get_db)
):
    """Update a signal message type"""
    msg_type = db.query(SignalMessageType).filter(
        SignalMessageType.id == message_type_id
    ).first()
    
    if not msg_type:
        raise HTTPException(status_code=404, detail="Message type not found")
    
    for key, value in data.model_dump().items():
        setattr(msg_type, key, value)
    
    db.commit()
    db.refresh(msg_type)
    return msg_type


@router.delete("/{message_type_id}")
async def delete_message_type(message_type_id: int, db: Session = Depends(get_db)):
    """Delete a signal message type"""
    msg_type = db.query(SignalMessageType).filter(
        SignalMessageType.id == message_type_id
    ).first()
    
    if not msg_type:
        raise HTTPException(status_code=404, detail="Message type not found")
    
    db.delete(msg_type)
    db.commit()
    return {"message": "Message type deleted"}
