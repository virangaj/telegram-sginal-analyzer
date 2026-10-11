import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr
from telethon.errors import RPCError, SessionPasswordNeededError

from app.telegram.listener import get_telegram_listener


def require_local_request(request: Request):
    local_hosts = {"localhost", "127.0.0.1", "::1", "testclient"}
    origin = request.headers.get("origin")
    if not request.client or request.client.host not in local_hosts or request.url.hostname not in local_hosts:
        raise HTTPException(403, "Telegram management is available locally only")
    if origin and urlparse(origin).hostname not in local_hosts:
        raise HTTPException(403, "Untrusted origin")


router = APIRouter(prefix="/api/telegram", tags=["telegram"], dependencies=[Depends(require_local_request)])
auth_lock = asyncio.Lock()
pending_phone = None
pending_hash = None
password_required = False


class PhoneRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{6,14}$")


class CodeRequest(PhoneRequest):
    code: SecretStr


class PasswordRequest(BaseModel):
    password: SecretStr


@router.get("/status")
async def status():
    listener = get_telegram_listener()
    authorized = bool(listener.client and await listener.client.is_user_authorized())
    return {
        "connected": authorized,
        "listening": authorized and listener.is_listening,
        "enabled_count": len(listener.enabled_chat_ids),
        "password_required": password_required,
    }


@router.post("/connect")
async def connect(data: PhoneRequest):
    global pending_phone, pending_hash, password_required
    async with auth_lock:
        listener = get_telegram_listener()
        await listener.connect()
        if await listener.client.is_user_authorized():
            return {"connected": True}
        try:
            sent = await listener.client.send_code_request(data.phone)
        except RPCError:
            raise HTTPException(400, "Telegram could not send a code. Check your phone number or try again later.")
        pending_phone, pending_hash = data.phone, sent.phone_code_hash
        password_required = False
        return {"connected": False, "code_sent": True}


@router.post("/verify-code")
async def verify_code(data: CodeRequest):
    global pending_phone, pending_hash, password_required
    async with auth_lock:
        listener = get_telegram_listener()
        if not pending_hash or pending_phone != data.phone or not listener.client:
            raise HTTPException(400, "Request a new login code first")
        try:
            await listener.client.sign_in(phone=data.phone, code=data.code.get_secret_value(), phone_code_hash=pending_hash)
        except SessionPasswordNeededError:
            password_required = True
            return {"connected": False, "password_required": True}
        except RPCError:
            raise HTTPException(400, "Invalid or expired code. Try again or request a new code.")
        pending_phone, pending_hash, password_required = None, None, False
        await listener.ensure_listening()
        return {"connected": True}


@router.post("/verify-2fa")
async def verify_password(data: PasswordRequest):
    global pending_phone, pending_hash, password_required
    async with auth_lock:
        listener = get_telegram_listener()
        if not password_required or not listener.client:
            raise HTTPException(400, "Verify a login code first")
        try:
            await listener.client.sign_in(password=data.password.get_secret_value())
        except RPCError:
            raise HTTPException(400, "Incorrect Telegram password")
        pending_phone, pending_hash, password_required = None, None, False
        await listener.ensure_listening()
        return {"connected": True}


@router.post("/logout")
async def logout():
    global pending_phone, pending_hash, password_required
    async with auth_lock:
        listener = get_telegram_listener()
        if listener.client:
            await listener._drain_background_tasks()
            try:
                await listener.client.log_out()
            except RPCError:
                raise HTTPException(502, "Telegram logout failed. Try again later.")
            await listener.disconnect()
        pending_phone, pending_hash, password_required = None, None, False
        return {"connected": False}