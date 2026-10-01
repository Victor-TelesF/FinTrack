import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest
from pydantic import SecretStr

from app.price_sources.brapi_source import BrapiPriceSource
from app.price_sources.types import MarketQuote, PriceKey, QuoteFailure

pytestmark = pytest.mark.asyncio
KEY = PriceKey("brapi", "PETR4", "BRL")


def row(symbol="PETR4", **data):
    return {
        "requestedSymbol": symbol, "symbol": symbol, "changed": False,
        "data": {
            "currency": "BRL", "regularMarketPrice": "35.123456789123456789",
            "regularMarketTime": "2026-10-01T10:00:00-03:00", **data,
        },
    }


async def fetch(handler, keys=(KEY,), token="synthetic-brapi-token", **kwargs):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await BrapiPriceSource(client, SecretStr(token), **kwargs).fetch_many(keys)


async def test_bearer_header_v2_url_and_decimal_json_precision(caplog):
    def handler(request):
        assert str(request.url) == "https://brapi.dev/api/v2/stocks/quote?symbols=PETR4"
        assert request.headers["Authorization"] == "Bearer synthetic-brapi-token"
        return httpx.Response(200, content=(
            '{"results":[{"requestedSymbol":"PETR4","symbol":"PETR4","changed":false,'
            '"data":{"currency":"BRL","regularMarketPrice":35.123456789123456789,'
            '"regularMarketTime":"2026-10-01T10:00:00-03:00"}}]}'
        ))

    before = datetime.now(timezone.utc)
    quote = (await fetch(handler))[KEY]
    assert isinstance(quote, MarketQuote)
    assert quote.price == Decimal("35.123456789123456789")
    assert quote.quoted_at == datetime(2026, 10, 1, 13, tzinfo=timezone.utc)
    assert before <= quote.fetched_at <= datetime.now(timezone.utc)
    assert quote.source == "brapi" and quote.currency == "BRL"
    assert "synthetic-brapi-token" not in caplog.text


@pytest.mark.parametrize("field,value,code", [
    ("regularMarketPrice", True, "invalid_price"),
    ("regularMarketPrice", None, "invalid_price"),
    ("regularMarketPrice", "NaN", "invalid_price"),
    ("regularMarketPrice", "Infinity", "invalid_price"),
    ("regularMarketPrice", "-1", "invalid_price"),
    ("regularMarketPrice", 0, "invalid_price"),
    ("regularMarketPrice", "abc", "invalid_price"),
    ("currency", "USD", "currency_mismatch"),
    ("currency", None, "currency_mismatch"),
    ("regularMarketTime", "2026-10-01T10:00:00", "invalid_timestamp"),
    ("regularMarketTime", "bad-date", "invalid_timestamp"),
    ("regularMarketTime", 123, "invalid_timestamp"),
])
async def test_rejects_invalid_market_values(field, value, code):
    result = await fetch(lambda _: httpx.Response(200, json={"results": [row(**{field: value})]}))
    assert result[KEY] == QuoteFailure(code)


async def test_missing_market_time_remains_unknown():
    result = await fetch(lambda _: httpx.Response(200, json={"results": [row(regularMarketTime=None)]}))
    assert result[KEY].quoted_at is None


@pytest.mark.parametrize("payload", [None, [], {}, {"results": {}}, {"results": [None]},
                                        {"results": [{}]}, {"results": [row(), row()]}])
async def test_rejects_malformed_or_duplicate_results(payload):
    assert (await fetch(lambda _: httpx.Response(200, json=payload)))[KEY] == QuoteFailure("invalid_response")


async def test_rejects_non_json():
    assert (await fetch(lambda _: httpx.Response(200, text="<html>bad</html>")))[KEY] == QuoteFailure("invalid_response")


async def test_does_not_silently_accept_renamed_or_converted_instruments():
    item = row()
    item.update(symbol="OTHER3", changed=True)
    assert (await fetch(lambda _: httpx.Response(200, json={"results": [item]})))[KEY] == QuoteFailure("identity_mismatch")


async def test_partial_batch_correlates_by_requested_symbol_not_order():
    fii = PriceKey("brapi", "HGLG11", "BRL")
    absent = PriceKey("brapi", "UNKNOWN1", "BRL")
    result = await fetch(lambda _: httpx.Response(200, json={"results": [row("HGLG11"), row()]}),
                         (KEY, fii, absent), batch_size=3)
    assert isinstance(result[KEY], MarketQuote)
    assert isinstance(result[fii], MarketQuote)
    assert result[absent] == QuoteFailure("missing_quote")


@pytest.mark.parametrize("status,code", [
    (400, "invalid_request"), (401, "authentication_error"), (403, "access_denied"),
    (404, "missing_quote"), (500, "provider_unavailable"), (503, "provider_unavailable"),
    (302, "invalid_response"),
])
async def test_http_failures_are_safe_and_never_retried(status, code, caplog):
    calls = 0
    def handler(_):
        nonlocal calls
        calls += 1
        return httpx.Response(status, text="synthetic-secret-echo", headers={"Location": "https://other.example"})
    result = await fetch(handler)
    assert result[KEY] == QuoteFailure(code)
    assert calls == 1
    assert "synthetic-secret-echo" not in str(result) + caplog.text


@pytest.mark.parametrize("exception,code", [(httpx.ReadTimeout, "timeout"), (httpx.ConnectError, "network_error")])
async def test_transport_errors(exception, code):
    def handler(request):
        raise exception("sensitive-message", request=request)
    assert (await fetch(handler))[KEY] == QuoteFailure(code)


async def test_missing_token_does_not_call_provider_even_for_sandbox_symbol():
    def handler(_):
        pytest.fail("Missing configuration must not trigger an HTTP call")
    assert (await fetch(handler, token=""))[KEY] == QuoteFailure("missing_token")


async def test_rate_limit_blocks_queued_and_new_calls_until_retry_after():
    now = [0.0]
    calls = 0
    def handler(_):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "120"})
        return httpx.Response(200, json={"results": [row()]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = BrapiPriceSource(client, SecretStr("test"), clock=lambda: now[0])
        other = PriceKey("brapi", "HGLG11", "BRL")
        result = await source.fetch_many([KEY, other])
        assert all(value == QuoteFailure("rate_limited", 120) for value in result.values())
        now[0] = 119
        assert (await source.fetch_many([KEY]))[KEY] == QuoteFailure("rate_limited", 1)
        assert calls == 1
        now[0] = 120
        assert isinstance((await source.fetch_many([KEY]))[KEY], MarketQuote)
        assert calls == 2


async def test_retry_after_http_date_and_invalid_values():
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=120))
    assert 118 <= BrapiPriceSource._retry_after(future) <= 120
    for value in (None, "bad", "NaN", "inf", "-1"):
        assert BrapiPriceSource._retry_after(value) == 60


async def test_batches_deduplicate_and_limit_concurrency():
    active = peak = 0
    calls = []
    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        symbols = request.url.params["symbols"].split(",")
        calls.append(symbols)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, json={"results": [row(symbol) for symbol in symbols]})
    keys = [PriceKey("brapi", f"ASSET{i}", "BRL") for i in range(7)]
    result = await fetch(handler, keys + keys, batch_size=2, max_concurrency=2)
    assert len(result) == 7 and len(calls) == 4
    assert peak == 2 and max(map(len, calls)) == 2


async def test_programming_errors_are_not_market_fallback():
    def handler(_):
        raise RuntimeError("bug")
    with pytest.raises(ExceptionGroup) as exc:
        await fetch(handler)
    assert isinstance(exc.value.exceptions[0], RuntimeError)


async def test_provider_cancellation_releases_semaphore():
    entered = asyncio.Event()
    calls = 0
    async def handler(_):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await asyncio.Event().wait()
        return httpx.Response(200, json={"results": [row()]} )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = BrapiPriceSource(client, SecretStr("test"))
        task = asyncio.create_task(source.fetch_many([KEY]))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        result = await asyncio.wait_for(source.fetch_many([KEY]), 1)
        assert isinstance(result[KEY], MarketQuote)
