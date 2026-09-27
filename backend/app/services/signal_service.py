"""
Signal service for parsing and storing signals
"""

import logging
import json
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.parsers.base import NormalizedSignal
from app.parsers.registry import get_registry
from app.database.models import (
    Signal, Message, SignalMessageType, SignalEntry,
    SignalTakeProfit, ParseStatus, SignalStatus
)

logger = logging.getLogger(__name__)


class SignalService:
    """Service for managing signals"""
    
    @staticmethod
    async def parse_and_store_signal(
        message_id: int,
        message_text: str,
        db: Session
    ) -> Optional[Signal]:
        """
        Parse a stored message and create a signal if successful.
        
        CRITICAL: Message is already stored. This attempts parsing.
        
        Args:
            message_id: ID of the Message record
            message_text: Text of the message
            db: Database session
            
        Returns:
            Stored Signal model or None if parsing failed
        """
        try:
            # Get the message record
            message = db.query(Message).filter(
                Message.id == message_id
            ).first()
            
            if not message:
                logger.error(f"Message {message_id} not found")
                return None
            
            # Get registry and parse
            registry = get_registry()
            normalized = await registry.parse_message(message_text)
            
            if not normalized:
                # Parsing failed - mark message and return
                message.parse_status = ParseStatus.FAILED
                message.parse_error = "No parser could handle this message"
                message.processed_at = datetime.utcnow()
                db.commit()
                logger.warning(f"Could not parse message {message_id}: {message_text[:100]}")
                return None
            
            # Resolve the configured message type from the parser that matched (if any)
            message_type = db.query(SignalMessageType).filter(
                SignalMessageType.parser_name == normalized.raw_signal_type
            ).first()

            # Parsing succeeded - store the signal
            signal = SignalService._store_normalized_signal(
                message_id, message_type.id if message_type else None, normalized, db
            )
            
            # Mark message as successfully parsed
            message.parse_status = ParseStatus.SUCCESS
            message.detected_message_type_id = message_type.id if message_type else None
            message.processed_at = datetime.utcnow()
            db.commit()
            
            return signal
            
        except Exception as e:
            logger.error(f"Error parsing signal: {e}", exc_info=True)
            # Mark message with error
            if message:
                message.parse_status = ParseStatus.FAILED
                message.parse_error = str(e)
                message.processed_at = datetime.utcnow()
                db.commit()
            return None
    
    @staticmethod
    def _store_normalized_signal(
        message_id: int,
        message_type_id: Optional[int],
        signal_data: NormalizedSignal,
        db: Session
    ) -> Signal:
        """Store a normalized signal in the database"""
        
        # Get message to get channel
        message = db.query(Message).filter(
            Message.id == message_id
        ).first()
        
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Create signal record
        db_signal = Signal(
            message_id=message_id,
            channel_id=message.channel_id,
            message_type_id=message_type_id,  # None if no configured SignalMessageType matched
            normalized_json=signal_data.model_dump_json(),
            symbol=signal_data.symbol,
            direction=signal_data.direction,
            order_type=signal_data.order_type,
            stop_loss=signal_data.stop_loss,
            confidence=signal_data.confidence,
            raw_signal_type=signal_data.raw_signal_type,
            status=SignalStatus.PENDING
        )
        db.add(db_signal)
        db.flush()  # Get the signal ID
        
        # Store entries
        for seq, entry_price in enumerate(signal_data.entries, start=1):
            entry = SignalEntry(
                signal_id=db_signal.id,
                entry_price=entry_price,
                sequence=seq
            )
            db.add(entry)
        
        # Store take profits
        for seq, tp_price in enumerate(signal_data.take_profits, start=1):
            tp = SignalTakeProfit(
                signal_id=db_signal.id,
                price=tp_price,
                sequence=seq
            )
            db.add(tp)
        
        db.commit()
        logger.info(f"Stored signal {db_signal.id} from message {message_id}")
        
        return db_signal
    
    @staticmethod
    async def reprocess_failed_messages(db: Session, limit: int = 100) -> int:
        """
        Reprocess all messages marked as FAILED.
        Use this after adding new parsers.
        
        Args:
            db: Database session
            limit: Maximum number of messages to reprocess
            
        Returns:
            Number of messages that were successfully reprocessed
        """
        failed_messages = db.query(Message).filter(
            Message.parse_status == ParseStatus.FAILED
        ).limit(limit).all()
        
        success_count = 0
        for message in failed_messages:
            try:
                signal = await SignalService.parse_and_store_signal(
                    message.id, message.raw_text, db
                )
                if signal:
                    success_count += 1
                    logger.info(f"Successfully reprocessed message {message.id}")
            except Exception as e:
                logger.error(f"Error reprocessing message {message.id}: {e}")
        
        return success_count
    
    @staticmethod
    def get_latest_signals(
        db: Session,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> list[Signal]:
        """Get latest signals"""
        query = db.query(Signal).order_by(Signal.created_at.desc())
        
        if symbol:
            query = query.filter(Signal.symbol == symbol)
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_signal_count_by_channel(db: Session) -> list[tuple]:
        """Get count of signals per channel"""
        return db.query(
            Signal.channel_id,
            func.count(Signal.id)
        ).group_by(Signal.channel_id).all()
