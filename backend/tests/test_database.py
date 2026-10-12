from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.database import base
from app.database.models import Base, Signal, SignalStatus


def test_init_db_repairs_legacy_signal_status_without_changing_valid_statuses(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(base, "engine", engine)
    Base.metadata.create_all(bind=engine)
    statuses = ["SUCCESS"] + [status.name for status in SignalStatus]
    with engine.begin() as connection:
        for message_id, status in enumerate(statuses, start=1):
            connection.execute(
                text(
                    "INSERT INTO signals "
                    "(message_id, channel_id, symbol, direction, order_type, status, "
                    "stop_loss, normalized_json) "
                    "VALUES (:message_id, 1, 'XAUUSD', 'BUY', 'LIMIT', :status, 2000, '{}')"
                ),
                {"message_id": message_id, "status": status},
            )

    base.init_db()
    base.init_db()

    with Session(engine) as session:
        signals = session.query(Signal).order_by(Signal.message_id).all()
        assert [signal.status for signal in signals] == [SignalStatus.PENDING] + list(SignalStatus)
    engine.dispose()


def test_init_db_adds_legacy_channel_category_as_cfds(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(base, "engine", engine)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE channels (id INTEGER PRIMARY KEY, platform VARCHAR NOT NULL, "
            "external_channel_id VARCHAR NOT NULL, channel_name VARCHAR NOT NULL, "
            "enabled BOOLEAN, parser_type VARCHAR, created_at DATETIME, updated_at DATETIME)"
        ))
        connection.execute(text(
            "INSERT INTO channels (id, platform, external_channel_id, channel_name, enabled) "
            "VALUES (1, 'telegram', '-100123', 'Existing room', 1)"
        ))

    base.init_db()
    base.init_db()

    with engine.connect() as connection:
        row = connection.execute(text("SELECT category FROM channels WHERE id = 1")).one()
        columns = {column["name"] for column in inspect(connection).get_columns("channels")}
        indexes = {index["name"] for index in inspect(connection).get_indexes("channels")}
    assert row.category == "cfds"
    assert "category" in columns
    assert "ix_channels_category" in indexes
    engine.dispose()