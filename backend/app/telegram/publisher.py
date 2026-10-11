import math
import re
import asyncio
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from telethon import functions, types
from telethon.errors import RPCError

from app.config import settings
from app.database.models import Signal, SignalStatus, TelegramPublication


logger = logging.getLogger(__name__)


def format_signal(signal: Signal) -> str:
    symbol = signal.symbol.upper().replace("/", "")
    if not re.fullmatch(r"[A-Z0-9]{2,20}", symbol):
        raise ValueError("Invalid instrument")
    if signal.direction not in ("BUY", "SELL") or signal.order_type not in ("MARKET", "LIMIT", "STOP"):
        raise ValueError("Unsupported signal direction or order type")
    entries = [entry.entry_price for entry in sorted(signal.entries, key=lambda item: item.sequence)]
    targets = [target.price for target in sorted(signal.take_profits, key=lambda item: item.sequence)]
    if not entries or not targets or any(not math.isfinite(price) or price <= 0 for price in entries + targets + [signal.stop_loss]):
        raise ValueError("Publication requires complete finite positive price levels")
    valid = (
        signal.stop_loss < min(entries) and all(target > max(entries) for target in targets)
        if signal.direction == "BUY" else
        signal.stop_loss > max(entries) and all(target < min(entries) for target in targets)
    )
    if not valid:
        raise ValueError("Stop loss and targets must be on the correct side of every entry")

    def price(value: float) -> str:
        return format(Decimal(str(value)).normalize(), "f")

    direction = signal.direction if signal.order_type == "MARKET" else f"{signal.direction} {signal.order_type}"
    lines = ["GOLD" if symbol in ("XAUUSD", "GOLD") else symbol, direction,
             "Entry: " + ", ".join(price(value) for value in entries)]
    lines.extend(f"TP{index}: {price(value)}" for index, value in enumerate(targets, 1))
    lines.append("SL: " + price(signal.stop_loss))
    text = "\n".join(lines)
    if len(text) > 4096:
        raise ValueError("Signal exceeds Telegram message length")
    return text


async def publish_signal(signal: Signal, db: Session, client, manual: bool = False) -> str:
    if not manual and not settings.telegram_auto_publish:
        return "disabled"
    if signal.message.source != "telegram" or signal.channel.external_channel_id == str(settings.telegram_publish_chat_id):
        return "skipped"
    if signal.status != SignalStatus.PENDING:
        return "skipped"
    try:
        body = format_signal(signal)
        raw_text = signal.message.raw_text.upper()
        if set(re.findall(r"\b(BUY|SELL)\b", raw_text)) != {signal.direction}:
            raise ValueError("Source direction is absent or ambiguous")
        symbol = signal.symbol.upper().replace("/", "")
        instrument_pattern = r"\b(?:GOLD|XAU\s*/?\s*USD)\b" if symbol in ("GOLD", "XAUUSD") else rf"\b{re.escape(symbol)}\b"
        if not re.search(instrument_pattern, raw_text.replace("/", "")):
            raise ValueError("Source instrument is absent")
    except (ValueError, TypeError):
        logger.warning("Signal %s is incomplete or invalid for publication", signal.id)
        return "invalid"
    if client is None or not client.is_connected() or not await client.is_user_authorized():
        logger.warning("Telegram publication unavailable: account not connected or authorized")
        return "unavailable"
    account = await client.get_me()
    if account is None:
        return "unavailable"
    publication = TelegramPublication(
        account_id=str(account.id), source_channel_id=signal.channel.external_channel_id,
        source_message_id=signal.message.external_message_id,
        destination_chat_id=str(settings.telegram_publish_chat_id), random_id=secrets.randbits(63) or 1,
        body=body, status="sending", created_at=datetime.now(timezone.utc),
    )
    try:
        db.add(publication)
        db.commit()
    except IntegrityError:
        db.rollback()
        return "already_recorded"
    try:
        peer = await asyncio.wait_for(client.get_input_entity(settings.telegram_publish_chat_id), timeout=20)
        request = functions.messages.SendMessageRequest(peer=peer, message=body, random_id=publication.random_id, no_webpage=True)
        result = await asyncio.wait_for(client(request), timeout=20)
        if isinstance(result, types.UpdateShortSentMessage):
            publication.destination_message_id = result.id
        else:
            for update in getattr(result, "updates", []):
                if isinstance(update, types.UpdateMessageID) and update.random_id == publication.random_id:
                    publication.destination_message_id = update.id
                    break
        publication.status = "sent"
        publication.sent_at = datetime.now(timezone.utc)
    except asyncio.CancelledError:
        publication.status = "unknown"
        publication.error_type = "CancelledError"
        db.commit()
        raise
    except RPCError as error:
        publication.status = "failed"
        publication.error_type = type(error).__name__
    except Exception as error:
        publication.status = "unknown"
        publication.error_type = type(error).__name__
    db.commit()
    logger.info("Telegram publication %s status: %s", publication.id, publication.status)
    return publication.status


async def delete_published_messages(signals: list[Signal], db: Session, client) -> int:
    if client is None or not client.is_connected() or not await client.is_user_authorized():
        raise ValueError("Connect the publishing Telegram account before deleting chat messages")
    account = await client.get_me()
    if account is None:
        raise ValueError("Telegram account is unavailable")
    publications = []
    for signal in signals:
        records = db.query(TelegramPublication).filter_by(
            source_channel_id=signal.channel.external_channel_id,
            source_message_id=signal.message.external_message_id,
            destination_chat_id=str(settings.telegram_publish_chat_id),
        ).all()
        for record in records:
            if record.status == "deleted":
                continue
            if record.account_id != str(account.id):
                raise ValueError("Reconnect the Telegram account that published this signal")
            if record.status != "sent" or record.destination_message_id is None:
                raise ValueError("Publication has no confirmed Telegram message ID; reconcile it in Telegram before deleting")
            publications.append(record)
    deleted = 0
    for record in publications:
        result = await asyncio.wait_for(client.delete_messages(
            int(record.destination_chat_id), [record.destination_message_id], revoke=True,
        ), timeout=20)
        if not result:
            raise ValueError("Telegram did not confirm message deletion")
        record.status = "deleted"
        db.commit()
        deleted += 1
    return deleted