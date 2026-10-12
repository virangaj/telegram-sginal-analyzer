import pytest
import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from pathlib import Path
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from telethon.errors import ChatWriteForbiddenError
from telethon import types

from app.database.models import Base, Channel, Message, Signal, SignalEntry, SignalTakeProfit, SignalStatus, TelegramPublication
from app.telegram.publisher import format_signal, publish_raw_message, publish_signal, delete_published_messages
from app.telegram import publisher, listener


def sample_signal(direction="BUY", order_type="MARKET"):
    return Signal(
        symbol="XAUUSD", direction=direction, order_type=order_type,
        stop_loss=1990 if direction == "BUY" else 2010,
        entries=[SignalEntry(entry_price=2000.12345, sequence=1)],
        take_profits=[SignalTakeProfit(price=2020 if direction == "BUY" else 1980, sequence=1)],
    )


def test_publication_format_preserves_price_precision_and_targets():
    signal = sample_signal()
    signal.take_profits.append(SignalTakeProfit(price=2030, sequence=2))
    assert format_signal(signal) == "GOLD\nBUY\nEntry: 2000.12345\nTP1: 2020\nTP2: 2030\nSL: 1990"
    assert "SELL LIMIT" in format_signal(sample_signal("SELL", "LIMIT"))


@pytest.mark.parametrize("field,value", [("entries", []), ("take_profits", []), ("stop_loss", float("nan")), ("stop_loss", 0), ("stop_loss", 2100), ("direction", "UNKNOWN")])
def test_invalid_signals_cannot_be_published(field, value):
    signal = sample_signal()
    setattr(signal, field, value)
    with pytest.raises(ValueError):
        format_signal(signal)


@pytest.fixture
def stored_signal(monkeypatch):
    monkeypatch.setattr(publisher.settings, "telegram_auto_publish", True)
    monkeypatch.setattr(publisher.settings, "telegram_publish_forex_chat_id", -1004302136634)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        channel = Channel(external_channel_id="-100123", channel_name="Source")
        db.add(channel)
        db.flush()
        message = Message(channel_id=channel.id, external_message_id="123", raw_text="GOLD BUY\nEntry: 2000.12345\nTP: 2020\nSL: 1990", received_at=datetime(2026, 1, 1))
        db.add(message)
        db.flush()
        signal = sample_signal()
        signal.message_id = message.id
        signal.channel_id = channel.id
        signal.normalized_json = "{}"
        signal.status = SignalStatus.PENDING
        db.add(signal)
        db.commit()
        yield signal, db
    engine.dispose()


def fake_client():
    client = AsyncMock()
    client.is_connected = lambda: True
    client.is_user_authorized.return_value = True
    client.get_me.return_value = SimpleNamespace(id=42)
    client.get_input_entity.return_value = "destination-peer"
    client.return_value = types.UpdateShortSentMessage(id=900, pts=1, pts_count=1, date=datetime.now())
    return client


def test_auto_publication_records_delivery_and_prevents_duplicates(stored_signal):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        assert await publish_signal(signal, db, client) == "sent"
        assert await publish_signal(signal, db, client) == "already_recorded"
        client.assert_awaited_once()
        client.get_input_entity.assert_awaited_with(-1004302136634)
        request = client.call_args.args[0]
        record = db.query(TelegramPublication).one()
        assert request.message == signal.message.raw_text
        assert request.random_id == record.random_id
        assert record.sent_at is not None
        assert record.destination_message_id == 900
        db.delete(signal)
        db.commit()
        assert db.query(TelegramPublication).count() == 1

    asyncio.run(check())


def test_unknown_delivery_is_not_blindly_retried(stored_signal):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        client.side_effect = TimeoutError()
        assert await publish_signal(signal, db, client) == "unknown"
        assert await publish_signal(signal, db, client) == "already_recorded"
        assert db.query(TelegramPublication).one().error_type == "TimeoutError"
        client.assert_awaited_once()
        assert db.get(Signal, signal.id).status == SignalStatus.PENDING

    asyncio.run(check())


def test_disabled_invalid_and_destination_signals_are_not_sent(stored_signal, monkeypatch):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        monkeypatch.setattr(publisher.settings, "telegram_auto_publish", False)
        assert await publish_signal(signal, db, client) == "disabled"
        monkeypatch.setattr(publisher.settings, "telegram_auto_publish", True)
        signal.stop_loss = 3000
        assert await publish_signal(signal, db, client) == "invalid"
        signal.channel.external_channel_id = "-1004302136634"
        assert await publish_signal(signal, db, client) == "skipped"
        client.assert_not_awaited()
        assert db.query(TelegramPublication).count() == 0
        telegram = listener.TelegramListener()
        telegram.enabled_chat_ids = {-1004302136634, -5349907572, -100123}
        assert not telegram.accepts_channel(-1004302136634)
        assert not telegram.accepts_channel(-5349907572)
        assert telegram.accepts_channel(-100123)

    asyncio.run(check())


def test_new_message_pipeline_sends_raw_recognized_signals(stored_signal, monkeypatch):
    from app.parsers.implementations import init_parsers

    signal, db = stored_signal
    sessions = sessionmaker(bind=db.get_bind())
    monkeypatch.setattr(listener, "SessionLocal", sessions)
    client = fake_client()
    monkeypatch.setattr(listener.get_telegram_listener(), "client", client)
    text = "Buy limit GOLD\nEntry: 2000\nTP: 2020\nSL: 1990"
    message = Message(channel_id=signal.channel_id, external_message_id="new-message", raw_text=text, received_at=datetime(2026, 1, 1))
    failed = Message(channel_id=signal.channel_id, external_message_id="commentary", raw_text="not a signal", received_at=datetime(2026, 1, 1))
    db.add_all([message, failed])
    db.commit()
    message_id, failed_id = message.id, failed.id
    init_parsers()

    async def check():
        await listener.MessageProcessor._parse_message_task(message_id, text)
        await listener.MessageProcessor._parse_message_task(failed_id, "not a signal")
        client.assert_awaited_once()
        assert db.query(TelegramPublication).one().status == "sent"
        assert db.query(TelegramPublication).one().body == text
        assert db.query(Signal).filter(Signal.message_id == message_id).count() == 1

    asyncio.run(check())


def test_permission_failure_and_disconnected_account_do_not_change_signal(stored_signal):
    async def check():
        signal, db = stored_signal
        assert await publish_signal(signal, db, None) == "unavailable"
        assert db.query(TelegramPublication).count() == 0
        client = fake_client()
        client.side_effect = ChatWriteForbiddenError(None)
        assert await publish_signal(signal, db, client) == "failed"
        assert db.query(TelegramPublication).one().error_type == "ChatWriteForbiddenError"
        assert signal.status == SignalStatus.PENDING

    asyncio.run(check())


def test_assumed_or_ambiguous_source_fields_are_not_published(stored_signal):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        for text in ("Entry: 2000\nSL: 1990\nTP: 2020", "GOLD BUY or SELL", "BUY\nEntry: 2000\nSL: 1990\nTP: 2020"):
            signal.message.raw_text = text
            assert await publish_signal(signal, db, client) == "invalid"
        client.assert_not_awaited()
        assert db.query(TelegramPublication).count() == 0

    asyncio.run(check())


def test_additive_sqlite_ledger_schema_is_idempotent_and_keeps_existing_data():
    schema = (Path(__file__).parents[1] / "app/database/migrations/001_telegram_publications.sql").read_text()
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE signals (id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO signals VALUES (1)")
    connection.executescript(schema)
    connection.executescript(schema)
    assert connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 1
    columns = {row[1] for row in connection.execute("PRAGMA table_info(telegram_publications)")}
    connection.executescript((Path(__file__).parents[1] / "app/database/migrations/002_publication_message_id.sql").read_text())
    columns = {row[1] for row in connection.execute("PRAGMA table_info(telegram_publications)")}
    assert columns == set(TelegramPublication.__table__.columns.keys())
    values = ("42", "-100123", "123", "-1004302136634", 1, "formatted signal", "sent", "2026-10-11")
    statement = "INSERT INTO telegram_publications (account_id, source_channel_id, source_message_id, destination_chat_id, random_id, body, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    connection.execute(statement, values)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(statement, values)
    connection.close()


def test_manual_send_and_exact_published_message_deletion(stored_signal, monkeypatch):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        monkeypatch.setattr(publisher.settings, "telegram_auto_publish", False)
        assert await publish_signal(signal, db, client, manual=True) == "sent"
        client.delete_messages.return_value = [SimpleNamespace(pts=1)]
        assert await delete_published_messages([signal], db, client) == 1
        client.delete_messages.assert_awaited_once_with(-1004302136634, [900], revoke=True)
        assert db.query(TelegramPublication).one().status == "deleted"
        assert await delete_published_messages([signal], db, client) == 0
        assert await publish_signal(signal, db, client, manual=True) == "already_recorded"
        assert signal.message.raw_text

    asyncio.run(check())


def test_legacy_unknown_message_id_does_not_delete_chat_messages(stored_signal):
    async def check():
        signal, db = stored_signal
        client = fake_client()
        assert await publish_signal(signal, db, client) == "sent"
        record = db.query(TelegramPublication).one()
        record.destination_message_id = None
        db.commit()
        with pytest.raises(ValueError, match="message ID"):
            await delete_published_messages([signal], db, client)
        client.delete_messages.assert_not_awaited()
        assert db.get(Signal, signal.id) is not None

    asyncio.run(check())


def test_explicit_crypto_short_source_can_be_published(stored_signal):
    async def check():
        signal, db = stored_signal
        signal.symbol = "BTCUSDT"
        signal.direction = "SELL"
        signal.stop_loss = 94000
        signal.entries[0].entry_price = 85500
        signal.take_profits[0].price = 77000
        signal.message.raw_text = "**FUTURE (SHORT)**\n**BTC / USDT**\nEnter Price: 85500\nTarget: 77000 (+100%)\nSL: 94000 (-100%)"
        db.commit()
        client = fake_client()
        assert await publish_signal(signal, db, client) == "sent"
        assert client.call_args.args[0].message == signal.message.raw_text

    asyncio.run(check())


def test_review_crypto_signal_is_forwarded_raw_to_crypto_destination(stored_signal, monkeypatch):
    from app.parsers.implementations import init_parsers
    from app.database.models import ParseStatus

    signal, db = stored_signal
    signal.channel.category = "crypto"
    monkeypatch.setattr(publisher.settings, "telegram_publish_crypto_chat_id", -5349907572)
    text = "XRP/USDT SHORT\nEntry: Market\nRange: 1.3928 - 1.6249\nTargets:\nTP1: 15%\nTP2: 30%\nStop Loss: 1.7083"
    message = Message(channel_id=signal.channel_id, external_message_id="review-crypto", raw_text=text, received_at=datetime(2026, 1, 1))
    db.add(message)
    db.commit()
    message_id = message.id
    init_parsers()
    sessions = sessionmaker(bind=db.get_bind())
    monkeypatch.setattr(listener, "SessionLocal", sessions)
    client = fake_client()
    monkeypatch.setattr(listener.get_telegram_listener(), "client", client)

    async def check():
        await listener.MessageProcessor._parse_message_task(message_id, text)
        db.refresh(message)
        assert message.parse_status == ParseStatus.REVIEW
        assert db.query(Signal).filter(Signal.message_id == message_id).count() == 0
        publication = db.query(TelegramPublication).filter_by(source_message_id="review-crypto").one()
        assert publication.destination_chat_id == "-5349907572"
        assert publication.body == text
        client.get_input_entity.assert_awaited_with(-5349907572)

    asyncio.run(check())