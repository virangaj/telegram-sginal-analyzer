from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

from app.config import settings
from app.market.providers.biquote import BiquoteCalendarSnapshot, BiquoteMarketDataProvider, BiquoteSymbol, MarketSnapshot


router = APIRouter(prefix="/api/market", tags=["market"])
_provider = None


def get_market_provider() -> BiquoteMarketDataProvider:
    global _provider
    if _provider is None:
        _provider = BiquoteMarketDataProvider(
            base_url=settings.biquote_base_url,
            poll_interval=settings.biquote_poll_interval_seconds,
            stale_after=settings.biquote_stale_after_seconds,
        )
    return _provider


async def close_market_provider():
    global _provider
    if _provider is not None:
        await _provider.close()
        _provider = None


@router.get("/calendar", response_model=BiquoteCalendarSnapshot)
async def get_economic_calendar(
    response: Response,
    from_time: Optional[datetime] = Query(default=None, alias="from"),
    to_time: Optional[datetime] = Query(default=None, alias="to"),
    countries: Optional[str] = None,
    importance: Optional[Literal["low", "medium", "high"]] = None,
    event_type: Optional[Literal["event", "indicator", "holiday"]] = Query(default=None, alias="type"),
    limit: int = 200,
):
    now = datetime.now(timezone.utc)
    start = from_time or now - timedelta(days=1)
    end = to_time or now + timedelta(days=7)
    if start.tzinfo is None or start.utcoffset() is None or end.tzinfo is None or end.utcoffset() is None:
        raise HTTPException(422, "Calendar range must use timezone-aware timestamps")
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if end <= start or end - start > timedelta(days=31):
        raise HTTPException(422, "Calendar range must be increasing and no longer than 31 days")
    if not 1 <= limit <= 500:
        raise HTTPException(422, "Calendar limit must be between 1 and 500")
    try:
        snapshot = await get_market_provider().get_calendar_events(
            start, end, countries=countries, importance=importance,
            event_type=event_type, limit=limit,
        )
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Economic calendar is temporarily unavailable")
    response.headers["Cache-Control"] = "no-store"
    return snapshot


@router.get("/symbols/search", response_model=list[BiquoteSymbol])
async def search_market_symbols(
    q: str = Query(min_length=2, max_length=64),
    category: Literal["crypto", "cfds"] = "cfds",
    limit: int = Query(default=20, ge=1, le=50),
):
    try:
        symbols = await get_market_provider().search_symbols(q, limit=limit)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Symbol search is temporarily unavailable")
    allowed_types = {"crypto"} if category == "crypto" else {"forex", "cfd", "commodity"}
    return [symbol for symbol in symbols if symbol.type and symbol.type.casefold() in allowed_types]


@router.get("/{symbol}", response_model=MarketSnapshot)
async def get_market_snapshot(symbol: str, response: Response):
    symbol = symbol.upper()
    if symbol not in {item.strip().upper() for item in settings.biquote_symbols.split(",") if item.strip()}:
        raise HTTPException(404, "Instrument is not configured for this quote feed")
    response.headers["Cache-Control"] = "no-store"
    return await get_market_provider().get_snapshot(symbol)