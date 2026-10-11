from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI
from sqlalchemy.pool import StaticPool
from telethon.errors import SessionPasswordNeededError

from app.database.models import Base, Channel
from app.telegram import listener
from app.api.routes import channels, telegram_auth
from app.database.base import get_db


def test_listener_refreshes_database_selection(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(listener, "SessionLocal", sessions)
    telegram = listener.TelegramListener()
    with sessions() as db:
        channel = Channel(platform="telegram", external_channel_id="-100123", channel_name="Gold", enabled=True)
        db.add(channel)
        db.commit()
        telegram.refresh_channels()
        assert telegram.accepts_channel(-100123)
        assert not telegram.accepts_channel(-100456)
        channel.enabled = False
        db.commit()
        telegram.refresh_channels()
        assert not telegram.accepts_channel(-100123)
    engine.dispose()


def test_discovery_preserves_saved_selection(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(listener, "SessionLocal", sessions)
    telegram = listener.TelegramListener()

    async def dialogs():
        yield SimpleNamespace(id=-100123, name="Renamed", is_channel=True, is_group=False)
        yield SimpleNamespace(id=-100456, name="New channel", is_channel=True, is_group=False)
        yield SimpleNamespace(id=789, name="Person", is_channel=False, is_group=False)

    telegram.client = SimpleNamespace(is_user_authorized=AsyncMock(return_value=True), iter_dialogs=dialogs)
    with sessions() as db:
        db.add(Channel(platform="telegram", external_channel_id="-100123", channel_name="Old", enabled=False))
        db.commit()
        asyncio.run(telegram.sync_channels(db))
        asyncio.run(telegram.sync_channels(db))
        stored = db.query(Channel).order_by(Channel.external_channel_id).all()
        assert len(stored) == 2
        assert stored[0].channel_name == "Renamed"
        assert not stored[0].enabled
        assert not stored[1].enabled
    engine.dispose()


def test_channel_api_persists_selection_and_blocks_remote_management(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(listener, "SessionLocal", sessions)
    telegram = listener.TelegramListener()
    monkeypatch.setattr(channels, "get_telegram_listener", lambda: telegram)
    with sessions() as db:
        channel = Channel(platform="telegram", external_channel_id="-100123", channel_name="Gold", enabled=False)
        db.add(channel)
        db.commit()
        channel_id = channel.id

    def database():
        with sessions() as db:
            yield db

    app = FastAPI()
    app.include_router(channels.router)
    app.dependency_overrides[get_db] = database

    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            response = await client.post(f"/api/channels/{channel_id}", json={"enabled": True})
            assert response.status_code == 200
            assert response.json()["enabled"]
            assert telegram.accepts_channel(-100123)
            assert (await client.get("/api/channels")).json()[0]["enabled"]
            response = await client.post(f"/api/channels/{channel_id}", json={"enabled": False})
            assert response.status_code == 200
            assert not telegram.accepts_channel(-100123)
            assert (await client.post("/api/channels/999", json={"enabled": True})).status_code == 404
            assert (await client.patch(f"/api/channels/{channel_id}", json={"enabled": True})).status_code == 405
            assert (await client.post("/api/channels/sync")).status_code == 409
            assert (await client.get("/api/channels", headers={"Origin": "https://untrusted.example"})).status_code == 403
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.0.2.1", 1234)), base_url="http://localhost") as client:
            assert (await client.get("/api/channels")).status_code == 403

    asyncio.run(check())
    engine.dispose()


def test_telegram_login_code_and_two_factor_flow(monkeypatch):
    telegram = SimpleNamespace(
        client=SimpleNamespace(
            is_user_authorized=AsyncMock(return_value=False),
            send_code_request=AsyncMock(return_value=SimpleNamespace(phone_code_hash="hash")),
            sign_in=AsyncMock(side_effect=[SessionPasswordNeededError(None), None]),
        ),
        connect=AsyncMock(), ensure_listening=AsyncMock(),
    )
    monkeypatch.setattr(telegram_auth, "get_telegram_listener", lambda: telegram)
    monkeypatch.setattr(telegram_auth, "pending_phone", None)
    monkeypatch.setattr(telegram_auth, "pending_hash", None)
    monkeypatch.setattr(telegram_auth, "password_required", False)
    monkeypatch.setattr(telegram_auth, "auth_lock", asyncio.Lock())

    async def check():
        phone = "+12345678901"
        assert (await telegram_auth.connect(telegram_auth.PhoneRequest(phone=phone)))["code_sent"]
        assert (await telegram_auth.verify_code(telegram_auth.CodeRequest(phone=phone, code="12345")))["password_required"]
        assert (await telegram_auth.verify_password(telegram_auth.PasswordRequest(password="test-password")))["connected"]
        assert telegram_auth.pending_hash is None
        assert not telegram_auth.password_required
        telegram.ensure_listening.assert_awaited_once()

    asyncio.run(check())


def test_local_cors_supports_credentials_and_channel_preflight():
    from app.main import app

    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            for origin in ("http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://[::1]:3000"):
                response = await client.get("/health", headers={"Origin": origin})
                assert response.status_code == 200
                assert response.headers["access-control-allow-origin"] == origin
                assert response.headers["access-control-allow-credentials"] == "true"
                for method in ("GET", "POST", "PATCH"):
                    preflight = await client.options(
                        "/api/channels/1",
                        headers={
                            "Origin": origin,
                            "Access-Control-Request-Method": method,
                            "Access-Control-Request-Headers": "content-type",
                        },
                    )
                    assert preflight.status_code == 200
                    assert preflight.headers["access-control-allow-origin"] == origin
            response = await client.options(
                "/api/channels/1",
                headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "PATCH"},
            )
            assert response.status_code == 400
            assert "access-control-allow-origin" not in response.headers

    asyncio.run(check())