from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

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