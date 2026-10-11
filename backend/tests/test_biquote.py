import asyncio
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import FastAPI

from app.market.providers.biquote import BiquoteMarketDataProvider


def tick(**overrides):
    return {
        "symbol": "XAUUSD", "bid": 2000, "ask": 2002, "mid": 2001,
        "timestamp": datetime.now(timezone.utc).isoformat(), "source": "Test broker",
        "stale": False, "marketState": "open", "quoteAgeSeconds": 0,
        "dayDiffPercent": 1.2, "last": 0, "volume": 0, **overrides,
    }


def test_midpoint_quote_cache_and_closed_market():
    async def check():
        requests = []
        data = tick()

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"XAUUSD": data})

        client = httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(handler))
        provider = BiquoteMarketDataProvider(client=client)
        snapshot = await provider.get_snapshot("XAUUSD")
        assert snapshot.price == 2001
        assert snapshot.source == "Test broker"
        assert snapshot.status == "live"
        assert await provider.get_bid_ask("XAUUSD") == (2000, 2002)
        assert len(requests) == 1
        assert requests[0].url.params.get_list("symbols") == ["XAUUSD"]
        data.update(marketState="closed", stale=True, timestamp=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat())
        provider._next_fetch.clear()
        closed = await provider.get_snapshot("XAUUSD")
        assert closed.status == "closed"
        assert closed.price == 2001
        assert closed.day_change_percent is None
        assert await provider.get_current_price("XAUUSD") is None
        await provider.close()

    asyncio.run(check())


def test_rate_limit_preserves_timestamp_and_stops_upstream_requests():
    async def check():
        responses = [httpx.Response(200, json={"XAUUSD": tick()}), httpx.Response(429, headers={"Retry-After": "60"})]
        calls = []

        def handler(request):
            calls.append(request)
            return responses.pop(0)

        provider = BiquoteMarketDataProvider(client=httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(handler)))
        first = await provider.get_snapshot("XAUUSD")
        provider._next_fetch.clear()
        failed = await provider.get_snapshot("XAUUSD")
        assert failed.status == "stale"
        assert failed.timestamp == first.timestamp
        assert failed.fetched_at == first.fetched_at
        assert failed.error
        await provider.get_snapshot("XAUUSD")
        assert len(calls) == 2
        await provider.close()

    asyncio.run(check())


def test_invalid_unknown_and_stale_quotes_are_not_live():
    async def check():
        for data in (tick(bid=2005), tick(timestamp="2026-01-01T00:00:00"), tick(source=""), tick(mid=0)):
            provider = BiquoteMarketDataProvider(client=httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"XAUUSD": data}))))
            assert (await provider.get_snapshot("XAUUSD")).status == "unavailable"
            await provider.close()
        for data, expected in ((tick(stale=True), "stale"), (tick(marketState="unknown"), "unknown"), (tick(timestamp=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()), "stale")):
            provider = BiquoteMarketDataProvider(client=httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"XAUUSD": data}))))
            assert (await provider.get_snapshot("XAUUSD")).status == expected
            assert await provider.get_current_price("XAUUSD") is None
            await provider.close()

    asyncio.run(check())


def test_market_api_returns_provenance_and_restricts_symbols(monkeypatch):
    from app.api.routes import market

    async def check():
        provider = BiquoteMarketDataProvider(client=httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"XAUUSD": tick()}))))
        monkeypatch.setattr(market, "get_market_provider", lambda: provider)
        app = FastAPI()
        app.include_router(market.router)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            response = await client.get("/api/market/xauusd")
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "Biquote"
            assert data["source"] == "Test broker"
            assert data["price_basis"] == "midpoint"
            assert data["status"] == "live"
            assert response.headers["cache-control"] == "no-store"
            assert (await client.get("/api/market/INVALID")).status_code == 404
        await provider.close()

    asyncio.run(check())


def test_timeout_and_recovery_do_not_fabricate_prices():
    async def check():
        calls = []

        def handler(request):
            calls.append(request)
            if len(calls) == 1:
                raise httpx.ReadTimeout("simulated outage", request=request)
            return httpx.Response(200, json={"XAUUSD": tick()})

        provider = BiquoteMarketDataProvider(client=httpx.AsyncClient(base_url="https://biquote.io", transport=httpx.MockTransport(handler)))
        unavailable = await provider.get_snapshot("XAUUSD")
        assert unavailable.status == "unavailable"
        assert unavailable.price is None
        assert unavailable.timestamp is None
        assert unavailable.error
        await provider.get_snapshot("XAUUSD")
        assert len(calls) == 1
        provider._next_fetch.clear()
        recovered = await provider.get_snapshot("XAUUSD")
        assert recovered.status == "live"
        assert recovered.error is None
        await provider.close()

    asyncio.run(check())