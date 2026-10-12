"""
Signal service for parsing and storing signals
"""

import logging
import json
import math
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, select, delete, inspect, Table, MetaData

from app.parsers.base import NormalizedSignal
from app.parsers.registry import get_registry
from app.database.models import (
    Signal, Message, Channel, SignalMessageType, SignalEntry,
    SignalTakeProfit, ParseStatus, SignalStatus, Analysis, AnalysisRun,
    MarketAnalysis, Trade, TradeSetup, TradeSetupEntry, TradeSetupTarget
)

logger = logging.getLogger(__name__)


class SignalService:
    """Service for managing signals"""

    @staticmethod
    def _clear_analysis(db: Session, signal_ids) -> None:
        if inspect(db.connection()).has_table("signal_events"):
            events = Table("signal_events", MetaData(), autoload_with=db.connection(), resolve_fks=False)
            db.execute(delete(events).where(events.c.signal_id.in_(signal_ids)))
        setup_ids = select(TradeSetup.id).where(TradeSetup.signal_id.in_(signal_ids))
        for model in (TradeSetupEntry, TradeSetupTarget):
            db.execute(delete(model).where(model.trade_setup_id.in_(setup_ids)), execution_options={"synchronize_session": False})
        for model in (TradeSetup, MarketAnalysis, AnalysisRun, Analysis):
            db.execute(delete(model).where(model.signal_id.in_(signal_ids)), execution_options={"synchronize_session": False})

    @staticmethod
    def delete_signals(db: Session, signal_id: Optional[int] = None) -> int:
        signal_ids = select(Signal.id)
        if signal_id is not None:
            signal_ids = signal_ids.where(Signal.id == signal_id)
        try:
            SignalService._clear_analysis(db, signal_ids)
            for model in (Trade, SignalEntry, SignalTakeProfit):
                db.execute(delete(model).where(model.signal_id.in_(signal_ids)), execution_options={"synchronize_session": False})
            result = db.execute(delete(Signal).where(Signal.id.in_(signal_ids)), execution_options={"synchronize_session": False})
            db.commit()
            db.expire_all()
            return result.rowcount
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_signal(db: Session, signal_id: int, changes: dict) -> Optional[Signal]:
        signal = db.get(Signal, signal_id)
        if signal is None:
            return None
        if not changes or any(value is None for key, value in changes.items() if key != "confidence"):
            raise ValueError("Provide at least one update; required price and instrument fields cannot be null")
        if db.query(Trade.id).filter(Trade.signal_id == signal_id).first():
            raise ValueError("Signals with trade records cannot be edited; preserve execution history")
        original = json.loads(signal.normalized_json)
        current = dict(original)
        current.update(
            symbol=signal.symbol, direction=signal.direction, order_type=signal.order_type,
            entries=[entry.entry_price for entry in sorted(signal.entries, key=lambda item: item.sequence)],
            stop_loss=signal.stop_loss,
            take_profits=[target.price for target in sorted(signal.take_profits, key=lambda item: item.sequence)],
            confidence=signal.confidence,
        )
        updated = NormalizedSignal.model_validate({**current, **changes})
        prices = updated.entries + updated.take_profits + [updated.stop_loss]
        if not updated.entries or not updated.take_profits or any(not math.isfinite(price) or price <= 0 for price in prices):
            raise ValueError("Entries, stop loss, and targets must contain finite positive prices")
        if not updated.symbol.strip() or updated.direction not in ("BUY", "SELL") or updated.order_type not in ("MARKET", "LIMIT", "STOP"):
            raise ValueError("Unsupported instrument, direction, or order type")
        if updated.direction == "BUY":
            valid = updated.stop_loss < min(updated.entries) and all(target > max(updated.entries) for target in updated.take_profits)
        else:
            valid = updated.stop_loss > max(updated.entries) and all(target < min(updated.entries) for target in updated.take_profits)
        if not valid:
            raise ValueError("Stop loss and targets must be on the correct side of every entry")
        history = list(original.get("manual_edits", []))
        history.append({"edited_at": datetime.now(timezone.utc).isoformat(), "before": NormalizedSignal.model_validate(current).model_dump()})
        data = updated.model_dump()
        data["manual_edits"] = history
        try:
            SignalService._clear_analysis(db, select(Signal.id).where(Signal.id == signal_id))
            for field in ("symbol", "direction", "order_type", "stop_loss", "confidence"):
                setattr(signal, field, getattr(updated, field))
            signal.entries = [SignalEntry(entry_price=price, sequence=sequence) for sequence, price in enumerate(updated.entries, 1)]
            signal.take_profits = [SignalTakeProfit(price=price, sequence=sequence) for sequence, price in enumerate(updated.take_profits, 1)]
            signal.normalized_json = json.dumps(data, allow_nan=False)
            signal.status = SignalStatus.PENDING
            db.commit()
            db.refresh(signal)
            return signal
        except Exception:
            db.rollback()
            raise
    
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
            normalized = await registry.parse_message(message_text, category=message.channel.category)
            
            if not normalized:
                # Parsing failed - mark message and return
                message.parse_status = ParseStatus.FAILED
                message.parse_error = f"No {message.channel.category} parser could handle this message"
                from app.parsers.implementations.gold import CryptoSignalParser, GoldSignalParser

                review_parser = (
                    CryptoSignalParser() if message.channel.category == "crypto"
                    else GoldSignalParser() if message.channel.category == "cfds"
                    else None
                )
                review_reason = (
                    review_parser.review_reason(message_text)
                    if review_parser and review_parser.can_parse(message_text)
                    else None
                )
                if review_reason:
                    message.parse_status = ParseStatus.REVIEW
                    message.parse_error = review_reason
                message.processed_at = datetime.utcnow()
                db.commit()
                logger.warning("Could not parse message %s", message_id)
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
        category: Optional[str] = None,
        limit: int = 10
    ) -> list[Signal]:
        """Get latest signals"""
        query = db.query(Signal).order_by(Signal.created_at.desc())
        
        if symbol:
            query = query.filter(Signal.symbol == symbol)

        if category:
            query = query.join(Channel, Signal.channel_id == Channel.id).filter(Channel.category == category)
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_signal_count_by_channel(db: Session) -> list[tuple]:
        """Get count of signals per channel"""
        return db.query(
            Signal.channel_id,
            func.count(Signal.id)
        ).group_by(Signal.channel_id).all()
