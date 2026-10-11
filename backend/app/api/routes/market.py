from fastapi import APIRouter, HTTPException, Response

from app.config import settings
from app.market.providers.biquote import BiquoteMarketDataProvider, MarketSnapshot


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


@router.get("/{symbol}", response_model=MarketSnapshot)
async def get_market_snapshot(symbol: str, response: Response):
    symbol = symbol.upper()
    if symbol not in {item.strip().upper() for item in settings.biquote_symbols.split(",") if item.strip()}:
        raise HTTPException(404, "Instrument is not configured for this quote feed")
    response.headers["Cache-Control"] = "no-store"
    return await get_market_provider().get_snapshot(symbol)