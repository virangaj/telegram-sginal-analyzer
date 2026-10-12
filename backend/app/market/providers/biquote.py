import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.market.base import MarketDataProvider, OHLC


class BiquoteTick(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    symbol: str
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    mid: float = Field(gt=0)
    timestamp: datetime
    source: str
    stale: bool
    marketState: Literal["open", "closed", "unknown"] = "unknown"
    quoteAgeSeconds: Optional[float] = Field(default=None, ge=0)
    dayDiffPercent: Optional[float] = None

    @model_validator(mode="after")
    def validate_quote(self):
        if self.timestamp.tzinfo is None or not self.source.strip():
            raise ValueError("Quote requires a timezone-aware source timestamp and feed identity")
        if self.bid > self.ask or not self.bid <= self.mid <= self.ask:
            raise ValueError("Quote requires bid <= midpoint <= ask")
        return self


class MarketSnapshot(BaseModel):
    provider: str = "Biquote"
    symbol: str
    price_basis: str = "midpoint"
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    quote_age_seconds: Optional[float] = None
    market_state: str = "unknown"
    status: Literal["live", "stale", "closed", "unknown", "unavailable"] = "unavailable"
    day_change_percent: Optional[float] = None
    error: Optional[str] = None


class BiquoteSymbol(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    exchange: Optional[str] = None
    source: Optional[str] = None
    digits: Optional[int] = None
    is_active: Optional[bool] = Field(default=None, validation_alias="isActive")
    has_data: Optional[bool] = Field(default=None, validation_alias="hasData")


class BiquoteCalendarEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    id: Optional[str] = None
    event_id: Optional[str] = Field(default=None, validation_alias="eventId")
    time: datetime
    period: Optional[str] = None
    country_code: Optional[str] = Field(default=None, validation_alias="countryCode")
    currency: Optional[str] = None
    name: Optional[str] = None
    importance: Optional[str] = None
    event_type: Optional[str] = Field(default=None, validation_alias="type")
    sector: Optional[str] = None
    unit: Optional[str] = None
    multiplier: Optional[str] = None
    digits: Optional[int] = None
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    revised_previous: Optional[float] = Field(default=None, validation_alias="revisedPrevious")
    revision: Optional[int] = None
    time_mode: Optional[str] = Field(default=None, validation_alias="timeMode")
    source_url: Optional[str] = Field(default=None, validation_alias="sourceUrl")
    source: Optional[str] = None

    @field_validator("actual", "forecast", "previous", "revised_previous", mode="before")
    @classmethod
    def empty_value_is_missing(cls, value):
        return None if value in ("", "-", "—") else value

    @field_validator("time")
    @classmethod
    def event_time_must_have_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Calendar event time must include a timezone")
        return value


class BiquoteCalendarSnapshot(BaseModel):
    provider: str = "Biquote"
    source: str = "Biquote Economic Calendar"
    requested_from: datetime
    requested_to: datetime
    fetched_at: datetime
    events: list[BiquoteCalendarEvent]


class BiquoteMarketDataProvider(MarketDataProvider):
    def __init__(self, base_url="https://biquote.io", poll_interval=1, stale_after=300, client=None):
        super().__init__("biquote")
        self.client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10, follow_redirects=True)
        self.poll_interval = max(1, poll_interval)
        self.stale_after = max(1, stale_after)
        self._quotes: dict[str, BiquoteTick] = {}
        self._fetched: dict[str, datetime] = {}
        self._next_fetch: dict[str, float] = {}
        self._errors: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._retry_at = 0.0
        self._calendar_lock = asyncio.Lock()
        self._calendar_cache_key = None
        self._calendar_cache_events: list[BiquoteCalendarEvent] = []
        self._calendar_cache_fetched_at: Optional[datetime] = None
        self._calendar_cache_expires_at = 0.0

    async def get_calendar_events(
        self,
        from_time: datetime,
        to_time: datetime,
        countries: Optional[str] = None,
        importance: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 200,
    ) -> BiquoteCalendarSnapshot:
        from_utc = from_time.astimezone(timezone.utc)
        to_utc = to_time.astimezone(timezone.utc)
        cache_key = (from_utc, to_utc, countries, importance, event_type, limit)
        async with self._calendar_lock:
            now = time.monotonic()
            if cache_key == self._calendar_cache_key and now < self._calendar_cache_expires_at:
                events = self._calendar_cache_events
                fetched_at = self._calendar_cache_fetched_at
            else:
                params = {
                    "from": from_utc.isoformat(),
                    "to": to_utc.isoformat(),
                    "limit": limit,
                }
                if countries:
                    params["countries"] = countries
                if importance:
                    params["importance"] = importance
                if event_type:
                    params["type"] = event_type
                response = await self.client.get("/api/Calendar", params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError("Calendar response must be a list")
                events = [BiquoteCalendarEvent.model_validate(item) for item in payload]
                events = sorted(
                    (event for event in events if from_utc <= event.time.astimezone(timezone.utc) < to_utc),
                    key=lambda event: event.time,
                )
                fetched_at = datetime.now(timezone.utc)
                self._calendar_cache_key = cache_key
                self._calendar_cache_events = events
                self._calendar_cache_fetched_at = fetched_at
                self._calendar_cache_expires_at = now + 60
        return BiquoteCalendarSnapshot(
            requested_from=from_utc,
            requested_to=to_utc,
            fetched_at=fetched_at,
            events=events,
        )

    async def search_symbols(self, query: str, limit: int = 25) -> list[BiquoteSymbol]:
        response = await self.client.get("/api/Symbols/search", params={"q": query, "limit": limit})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Symbol search response must be a list")
        return [BiquoteSymbol.model_validate(item) for item in payload]

    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        async with self._lock:
            now = time.monotonic()
            if now >= self._retry_at and now >= self._next_fetch.get(symbol, 0):
                self._next_fetch[symbol] = now + self.poll_interval
                try:
                    response = await self.client.get("/api/latest", params=[("symbols", symbol)])
                    if response.status_code in (429, 503):
                        try:
                            retry = float(response.headers.get("Retry-After", "60"))
                            if not math.isfinite(retry):
                                retry = 60
                        except ValueError:
                            retry = 60
                        self._retry_at = now + max(1, min(retry, 3600))
                    response.raise_for_status()
                    quote = BiquoteTick.model_validate(response.json()[symbol])
                    if quote.symbol != symbol or quote.timestamp > datetime.now(timezone.utc):
                        raise ValueError("Quote symbol or timestamp mismatch")
                    self._quotes[symbol] = quote
                    self._fetched[symbol] = datetime.now(timezone.utc)
                    self._errors.pop(symbol, None)
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    self._errors[symbol] = "Quote refresh failed; retrying automatically"
                    self._next_fetch[symbol] = max(self._next_fetch[symbol], now + 5)

            quote = self._quotes.get(symbol)
            if quote is None:
                return MarketSnapshot(symbol=symbol, error=self._errors.get(symbol, "Provider is temporarily unavailable"))
            age = max(0, (datetime.now(timezone.utc) - quote.timestamp).total_seconds())
            if quote.quoteAgeSeconds is not None:
                age = max(age, quote.quoteAgeSeconds + (datetime.now(timezone.utc) - self._fetched[symbol]).total_seconds())
            failed = symbol in self._errors or time.monotonic() < self._retry_at
            state = "closed" if quote.marketState == "closed" else "stale" if failed or quote.stale or age > self.stale_after else "live" if quote.marketState == "open" else "unknown"
            return MarketSnapshot(
                symbol=symbol, price=quote.mid, bid=quote.bid, ask=quote.ask,
                source=quote.source, timestamp=quote.timestamp, fetched_at=self._fetched[symbol],
                quote_age_seconds=age, market_state=quote.marketState, status=state,
                day_change_percent=quote.dayDiffPercent if state == "live" else None,
                error=self._errors.get(symbol, "Provider rate limit or outage; retrying automatically" if failed else None),
            )

    async def get_current_price(self, symbol: str) -> Optional[float]:
        snapshot = await self.get_snapshot(symbol)
        return snapshot.price if snapshot.status == "live" else None

    async def get_bid_ask(self, symbol: str) -> Optional[tuple[float, float]]:
        snapshot = await self.get_snapshot(symbol)
        if snapshot.status != "live":
            return None
        return snapshot.bid, snapshot.ask

    async def is_market_open(self, symbol: str) -> bool:
        return (await self.get_snapshot(symbol)).market_state == "open"

    async def get_ohlc(self, symbol: str, timeframe: str, limit: int = 100) -> list[OHLC]:
        raise NotImplementedError("Biquote historical candle provenance is not integrated; this adapter supplies quotes only")

    async def close(self):
        await self.client.aclose()