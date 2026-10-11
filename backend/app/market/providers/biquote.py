import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

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