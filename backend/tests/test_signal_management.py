import asyncio
import json
from datetime import datetime

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import signals
from app.database import base
from app.database.models import (
    Base, Channel, Message, Signal, SignalEntry, SignalTakeProfit, MarketCandle,
    Analysis, AnalysisRun, MarketAnalysis, TradeSetup, TradeSetupEntry, TradeSetupTarget, Trade,
)
from app.services.signal_service import SignalService


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE signal_events (id INTEGER PRIMARY KEY, signal_id INTEGER NOT NULL REFERENCES signals(id))"))
        connection.execute(text("CREATE TABLE sr_zones (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE zone_touch_events (id INTEGER PRIMARY KEY, zone_id INTEGER NOT NULL REFERENCES sr_zones(id))"))
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(base, "engine", engine)
    with sessions() as db:
        channel = Channel(external_channel_id="-100123", channel_name="Gold")
        db.add(channel)
        db.flush()
        for number in (1, 2):
            message = Message(channel_id=channel.id, external_message_id=str(number), raw_text="original", received_at=datetime(2026, 1, 1))
            db.add(message)
            db.flush()
            signal = Signal(message_id=message.id, channel_id=channel.id, symbol="XAUUSD", direction="BUY", order_type="LIMIT", stop_loss=1990, normalized_json=json.dumps({"symbol": "XAUUSD", "direction": "BUY", "order_type": "LIMIT", "entries": [2000], "stop_loss": 1990, "take_profits": [2020]}))
            signal.entries = [SignalEntry(entry_price=2000, sequence=1)]
            signal.take_profits = [SignalTakeProfit(price=2020, sequence=1)]
            db.add(signal)
            db.flush()
            run = AnalysisRun(signal_id=signal.id, market_timestamp=datetime(2026, 1, 1))
            db.add(run)
            db.flush()
            analysis = MarketAnalysis(signal_id=signal.id, analysis_run_id=run.id)
            db.add(analysis)
            db.flush()
            setup = TradeSetup(signal_id=signal.id, analysis_id=analysis.id, analysis_run_id=run.id, direction="BUY", stop_loss=1990)
            setup.entries = [TradeSetupEntry(price=2000, allocation_percent=1, sequence=1)]
            setup.targets = [TradeSetupTarget(price=2020, sequence=1)]
            db.add(setup)
            db.add(Analysis(signal_id=signal.id, timeframe="1H", analysis_json="{}"))
        db.add(MarketCandle(symbol="XAUUSD", timeframe="1H", timestamp=datetime(2026, 1, 1), open=2000, high=2020, low=1990, close=2010))
        db.commit()
        db.execute(text("INSERT INTO signal_events (signal_id) VALUES (1), (2)"))
        db.execute(text("INSERT INTO sr_zones (id) VALUES (1)"))
        db.execute(text("INSERT INTO zone_touch_events (zone_id) VALUES (1)"))
        db.commit()
        yield db
    engine.dispose()


def test_delete_one_and_all_removes_dependencies_but_preserves_messages(database):
    db = database
    db.add(Trade(signal_id=1, status="CLOSED"))
    db.commit()
    assert SignalService.delete_signals(db, 1) == 1
    assert db.get(Signal, 1) is None
    assert db.get(Signal, 2) is not None
    assert db.query(Trade).count() == 0
    assert db.query(TradeSetup).count() == 1
    assert db.execute(text("SELECT COUNT(*) FROM signal_events")).scalar() == 1
    assert SignalService.delete_signals(db) == 1
    assert SignalService.delete_signals(db) == 0
    for model in (Signal, SignalEntry, SignalTakeProfit, Analysis, AnalysisRun, MarketAnalysis, TradeSetup, TradeSetupEntry, TradeSetupTarget):
        assert db.query(model).count() == 0
    assert db.query(Message).count() == 2
    assert db.query(Channel).count() == 1
    assert db.query(MarketCandle).count() == 1
    assert db.execute(text("SELECT COUNT(*) FROM signal_events")).scalar() == 0


def test_update_keeps_raw_evidence_and_invalidates_analysis(database):
    db = database
    updated = SignalService.update_signal(db, 1, {"entries": [2001, 2002], "stop_loss": 1980, "take_profits": [2030, 2040]})
    assert [entry.entry_price for entry in updated.entries] == [2001, 2002]
    assert [target.price for target in updated.take_profits] == [2030, 2040]
    data = json.loads(updated.normalized_json)
    assert data["entries"] == [2001, 2002]
    assert data["manual_edits"][0]["before"]["entries"] == [2000]
    assert updated.message.raw_text == "original"
    assert db.query(TradeSetup).filter_by(signal_id=1).count() == 0
    assert db.query(AnalysisRun).filter_by(signal_id=2).count() == 1
    with pytest.raises(ValueError):
        SignalService.update_signal(db, 1, {"stop_loss": 3000})
    assert db.get(Signal, 1).stop_loss == 1980


def test_market_clear_preserves_signals_and_sources(database):
    assert base.clear_market_data() == {"market_candles": 1, "sr_zones": 1, "zone_touch_events": 1}
    assert base.clear_market_data() == {"market_candles": 0, "sr_zones": 0, "zone_touch_events": 0}
    assert database.query(Signal).count() == 2
    assert database.query(Message).count() == 2
    assert database.execute(text("SELECT COUNT(*) FROM signal_events")).scalar() == 2


def test_trade_history_cannot_be_overwritten(database):
    database.add(Trade(signal_id=1, status="CLOSED"))
    database.commit()
    with pytest.raises(ValueError, match="trade records"):
        SignalService.update_signal(database, 1, {"stop_loss": 1980})
    assert database.get(Signal, 1).stop_loss == 1990
    assert database.query(TradeSetup).filter_by(signal_id=1).count() == 1


def test_delete_rolls_back_dependency_cleanup_on_failure(database):
    engine = database.get_bind()

    def fail_delete(connection, cursor, statement, parameters, context, many):
        if statement.startswith("DELETE FROM signals "):
            raise RuntimeError("simulated failure")

    event.listen(engine, "before_cursor_execute", fail_delete)
    try:
        with pytest.raises(RuntimeError, match="simulated failure"):
            SignalService.delete_signals(database, 1)
    finally:
        event.remove(engine, "before_cursor_execute", fail_delete)
    assert database.get(Signal, 1) is not None
    assert database.query(TradeSetup).filter_by(signal_id=1).count() == 1
    assert database.execute(text("SELECT COUNT(*) FROM signal_events")).scalar() == 2


def test_management_api_validation_and_confirmation(database):
    app = FastAPI()
    app.include_router(signals.router)
    app.dependency_overrides[base.get_db] = lambda: database

    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            assert (await client.delete("/api/signals")).status_code == 400
            for payload in ({}, {"entries": []}, {"entries": [-1]}, {"stop_loss": None}, {"stop_loss": 3000}, {"confidence": 2}, {"unexpected": True}):
                assert (await client.post("/api/signals/1", json=payload)).status_code == 422
            response = await client.post("/api/signals/1", json={"entries": [2001], "take_profits": [2030]})
            assert response.status_code == 200
            assert response.json()["entries"] == [2001]
            assert response.json()["channel_name"] == "Gold"
            listed = await client.get("/api/signals")
            assert all(item["channel_name"] == "Gold" for item in listed.json())
            assert (await client.post("/api/signals/999", json={"stop_loss": 1990})).status_code == 404
            assert (await client.delete("/api/signals/999")).status_code == 404
            assert (await client.delete("/api/signals/1", headers={"Origin": "https://untrusted.example"})).status_code == 403
            assert (await client.delete("/api/signals/1")).json() == {"deleted": 1}
            assert (await client.delete("/api/signals?confirm=true")).json() == {"deleted": 1}

    asyncio.run(check())


def test_signal_category_filter_uses_assigned_channel_category(database):
    crypto_channel = Channel(platform="telegram", external_channel_id="-100999", channel_name="Crypto room", category="crypto")
    database.add(crypto_channel)
    database.flush()
    message = Message(channel_id=crypto_channel.id, external_message_id="crypto", raw_text="BTCUSDT BUY", received_at=datetime(2026, 1, 2))
    database.add(message)
    database.flush()
    crypto_signal = Signal(message_id=message.id, channel_id=crypto_channel.id, symbol="BTCUSDT", direction="BUY", order_type="MARKET", stop_loss=90, normalized_json="{}")
    crypto_signal.entries = [SignalEntry(entry_price=100, sequence=1)]
    crypto_signal.take_profits = [SignalTakeProfit(price=120, sequence=1)]
    database.add(crypto_signal)
    database.commit()

    assert [signal.symbol for signal in SignalService.get_latest_signals(database, category="crypto")] == ["BTCUSDT"]
    assert {signal.symbol for signal in SignalService.get_latest_signals(database, category="cfds")} == {"XAUUSD"}

    app = FastAPI()
    app.include_router(signals.router)
    app.dependency_overrides[base.get_db] = lambda: database

    async def check_api():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            crypto = await client.get("/api/signals", params={"category": "crypto"})
            cfds = await client.get("/api/signals", params={"category": "cfds"})
            invalid = await client.get("/api/signals", params={"category": "stocks"})
            assert [signal["category"] for signal in crypto.json()] == ["crypto"]
            assert all(signal["category"] == "cfds" for signal in cfds.json())
            assert invalid.status_code == 422

    asyncio.run(check_api())


@pytest.mark.parametrize("category,text,expected_symbol", [
    ("crypto", "BTCUSDT BUY 100\nTP: 120\nSL: 90", "BTCUSDT"),
    ("cfds", "GOLD BUY 2000\nTP: 2020\nSL: 1990", "XAUUSD"),
    ("crypto", "GOLD BUY 2000\nTP: 2020\nSL: 1990", None),
    ("cfds", "BTCUSDT BUY 100\nTP: 120\nSL: 90", None),
    ("stocks", "GOLD BUY 2000\nTP: 2020\nSL: 1990", None),
])
def test_ingestion_routes_parsing_by_channel_category(database, category, text, expected_symbol):
    from app.parsers.implementations import init_parsers
    from app.database.models import ParseStatus

    init_parsers()
    channel = database.query(Channel).first()
    channel.category = category
    message = Message(channel_id=channel.id, external_message_id="category-routing", raw_text=text, received_at=datetime(2026, 1, 2))
    database.add(message)
    database.commit()

    result = asyncio.run(SignalService.parse_and_store_signal(message.id, text, database))
    database.refresh(message)
    assert message.raw_text == text
    if expected_symbol:
        assert result.symbol == expected_symbol
        assert result.channel.category == category
        assert message.parse_status == ParseStatus.SUCCESS
    else:
        assert result is None
        assert message.parse_status == ParseStatus.FAILED
        assert database.query(Signal).filter_by(message_id=message.id).count() == 0


def test_partial_crypto_message_is_stored_for_review_without_signal(database):
    from app.parsers.implementations import init_parsers
    from app.database.models import ParseStatus

    init_parsers()
    channel = database.query(Channel).first()
    channel.category = "crypto"
    text = "Coin: PNUT /USDT\nDirection: LONG\nEntry: Limit Order\nRange: 0.04797 - 0.03892\nTP1: 15%\nStop Loss: 0.03723"
    message = Message(channel_id=channel.id, external_message_id="partial-crypto", raw_text=text, received_at=datetime(2026, 1, 2))
    database.add(message)
    database.commit()
    result = asyncio.run(SignalService.parse_and_store_signal(message.id, text, database))
    assert result is None
    database.refresh(message)
    assert message.parse_status == ParseStatus.REVIEW
    assert "Entry range" in message.parse_error
    assert message.raw_text == text
    assert database.query(Signal).filter_by(message_id=message.id).count() == 0