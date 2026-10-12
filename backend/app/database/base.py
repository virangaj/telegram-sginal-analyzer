"""
Database initialization and session management
"""

from sqlalchemy import create_engine, text, delete, inspect, Table, MetaData
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.database.models import Base, SignalStatus, MarketCandle


# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_channel_category_column() -> None:
    """Add channel categories to existing databases without changing channel selection."""
    with engine.begin() as connection:
        channel_columns = {column["name"] for column in inspect(connection).get_columns("channels")}
        if "category" not in channel_columns:
            connection.execute(text("ALTER TABLE channels ADD COLUMN category VARCHAR NOT NULL DEFAULT 'cfds'"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_channels_category ON channels (category)"))


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    ensure_channel_category_column()
    with engine.begin() as connection:
        publication_tables = set(inspect(connection).get_table_names())
        if "telegram_publications" in publication_tables:
            columns = {column["name"] for column in inspect(connection).get_columns("telegram_publications")}
            if "destination_message_id" not in columns:
                connection.execute(text("ALTER TABLE telegram_publications ADD COLUMN destination_message_id INTEGER"))
        connection.execute(
            text("UPDATE signals SET status = :pending WHERE status = :legacy_status"),
            {"pending": SignalStatus.PENDING.name, "legacy_status": "SUCCESS"},
        )


def clear_market_data() -> dict[str, int]:
    """Clear market candles and legacy zones, preserving signals and their sources."""
    with engine.begin() as connection:
        counts = {}
        inspector = inspect(connection)
        for name in ("zone_touch_events", "sr_zones"):
            if inspector.has_table(name):
                table = Table(name, MetaData(), autoload_with=connection, resolve_fks=False)
                counts[name] = connection.execute(delete(table)).rowcount
        counts["market_candles"] = connection.execute(delete(MarketCandle)).rowcount
        return counts


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
