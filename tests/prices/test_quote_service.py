import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.price_sources.brapi_source import BrapiPriceSource
from app.price_sources.cache import QuoteCache
from app.price_sources.exceptions import QuoteConfigurationError, QuoteUnavailableError
from app.price_sources.types import MarketQuote, PriceKey, PriceRequest, QuoteFailure
from app.service.quote_service import QuoteService

pytestmark = pytest.mark.asyncio


def request(symbol="PETR4"):
    return PriceRequest(uuid4(), "brapi", symbol, "BRL")


class FakeSource:
    batch_size = 2

    def __init__(self):
        self.calls = []
        self.failure = None

    async def fetch_many(self, keys):
        self.calls.append(keys)
        return {
            key: self.failure or MarketQuote(
                Decimal("35"), key.currency, key.source, None, datetime.now(timezone.utc),
            ) for key in keys
        }


async def test_empty_input_and_deduplication_preserve_internal_ids():
    source = FakeSource()
    service = QuoteService(source, QuoteCache(10, 60))
    assert await service.get_quotes([]) == {}
    assert source.calls == []
    requests = [request(), request(), request("HGLG11"), request("VALE3")]
    quotes = await service.get_quotes(requests)
    assert set(quotes) == {item.asset_id for item in requests}
    assert len(source.calls) == 2
    assert sum(map(len, source.calls)) == 3
    assert all(q.price == Decimal("35") and not q.from_cache for q in quotes.values())
    cached = await service.get_quotes(requests)
    assert all(q.from_cache for q in cached.values())
    assert len(source.calls) == 2
    assert cached[requests[0].asset_id].fetched_at == quotes[requests[0].asset_id].fetched_at


async def test_cache_expiry_never_falls_back_to_stale_or_manual_price():
    now = [0.0]
    source = FakeSource()
    service = QuoteService(source, QuoteCache(10, 60, clock=lambda: now[0]))
    item = request()
    await service.get_quotes([item])
    now[0] = 60
    source.failure = QuoteFailure("timeout")
    with pytest.raises(QuoteUnavailableError) as exc:
        await service.get_quotes([item])
    assert exc.value.failures == {item.asset_id: QuoteFailure("timeout")}
    source.failure = None
    assert not (await service.get_quotes([item]))[item.asset_id].from_cache
    assert len(source.calls) == 3


async def test_lru_cache_is_bounded_and_key_includes_source_and_currency():
    cache = QuoteCache(2, 60)
    base = PriceKey("brapi", "PETR4", "BRL")
    usd = replace(base, currency="USD")
    other = replace(base, source="other")
    quote = MarketQuote(Decimal("35"), "BRL", "brapi", None, datetime.now(timezone.utc))
    cache.put(base, quote)
    cache.put(usd, replace(quote, currency="USD"))
    assert cache.get(base) == quote
    cache.put(other, replace(quote, source="other"))
    assert cache.get(usd) is None
    assert cache.get(base).currency == "BRL"
    assert cache.get(other).source == "other"


async def test_concurrent_callers_share_fetch_and_cancelled_waiter_does_not_cancel_it():
    entered, release = asyncio.Event(), asyncio.Event()
    source = FakeSource()
    original = source.fetch_many
    async def fetch(keys):
        entered.set()
        await release.wait()
        return await original(keys)
    source.fetch_many = fetch
    service = QuoteService(source, QuoteCache(10, 60))
    first, second = request(), request()
    task1 = asyncio.create_task(service.get_quotes([first]))
    await entered.wait()
    task2 = asyncio.create_task(service.get_quotes([second]))
    await asyncio.sleep(0)
    task1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task1
    release.set()
    result = await asyncio.wait_for(task2, 1)
    assert set(result) == {second.asset_id} and len(source.calls) == 1
    assert (await service.get_quotes([first]))[first.asset_id].from_cache
    assert service._inflight == {}


async def test_failure_releases_shared_task_and_retry_can_succeed():
    source = FakeSource()
    source.failure = QuoteFailure("authentication_error")
    service = QuoteService(source, QuoteCache(10, 60))
    first, second = request(), request()
    results = await asyncio.gather(service.get_quotes([first]), service.get_quotes([second]), return_exceptions=True)
    assert all(isinstance(result, QuoteUnavailableError) for result in results)
    assert len(source.calls) == 1 and service._inflight == {}
    source.failure = None
    await service.get_quotes([first])
    assert len(source.calls) == 2


async def test_partial_provider_response_fails_whole_request_but_caches_valid_items():
    first, second = request(), request("UNKNOWN1")
    class PartialSource(FakeSource):
        async def fetch_many(self, keys):
            results = await super().fetch_many(keys)
            results.pop(second.key, None)
            return results
    source = PartialSource()
    service = QuoteService(source, QuoteCache(10, 60))
    with pytest.raises(QuoteUnavailableError) as exc:
        await service.get_quotes([first, second])
    assert exc.value.failures == {second.asset_id: QuoteFailure("missing_quote")}
    assert (await service.get_quotes([first]))[first.asset_id].from_cache
    assert len(source.calls) == 1


@pytest.mark.parametrize("changes", [
    {"source": "manual"}, {"currency": "USD"}, {"currency": ""},
    {"external_price_id": ""}, {"external_price_id": "PETR4/../../"},
])
async def test_invalid_configuration_does_not_fetch(changes):
    item = replace(request(), **changes)
    source = FakeSource()
    service = QuoteService(source, QuoteCache(10, 60))
    with pytest.raises(QuoteConfigurationError) as exc:
        await service.get_quotes([item])
    assert exc.value.asset_ids == [item.asset_id] and source.calls == []


async def test_conflicting_internal_identity_is_not_overwritten():
    item = request()
    service = QuoteService(FakeSource(), QuoteCache(10, 60))
    with pytest.raises(QuoteConfigurationError):
        await service.get_quotes([item, replace(item, external_price_id="VALE3")])


async def test_shutdown_cancels_active_fetches_and_drains_all_tasks():
    entered, cancelled = asyncio.Event(), asyncio.Event()
    class SlowSource(FakeSource):
        async def fetch_many(self, keys):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
    service = QuoteService(SlowSource(), QuoteCache(10, 60))
    waiter = asyncio.create_task(service.get_quotes([request()]))
    await entered.wait()
    await service.aclose()
    assert cancelled.is_set() and service._inflight == {}
    with pytest.raises(asyncio.CancelledError):
        await waiter
    with pytest.raises(RuntimeError, match="closed"):
        await service.get_quotes([])


async def test_http_to_service_pipeline_uses_free_plan_limits_and_warm_cache():
    calls = []
    def handler(req):
        symbol = req.url.params["symbols"]
        calls.append(symbol)
        assert "," not in symbol
        return httpx.Response(200, json={"results": [{
            "requestedSymbol": symbol, "symbol": symbol, "changed": False,
            "data": {"regularMarketPrice": 35, "currency": "BRL", "regularMarketTime": None},
        }]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = QuoteService(BrapiPriceSource(client, SecretStr("test")), QuoteCache(10, 60))
        items = [request(), request(), request("HGLG11")]
        assert len(await service.get_quotes(items)) == 3
        assert all(q.from_cache for q in (await service.get_quotes(items)).values())
        assert calls == ["PETR4", "HGLG11"]
        await service.aclose()
