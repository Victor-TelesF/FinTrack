from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import select

from app.dependencies import get_quote_service
from app.config import settings
from app.models import AssetModel
from app.price_sources.brapi_source import BrapiPriceSource
from app.price_sources.cache import QuoteCache
from app.service.quote_service import QuoteService
from tests.app.routers.test_portfolio_router import register_and_login

pytestmark = pytest.mark.asyncio
PATHS = ["/api/v2/portfolios/positions", "/api/v2/portfolios/summary"]


@pytest_asyncio.fixture
async def market(test_app, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    state = SimpleNamespace(calls=[], now=0, failure=None, price="35", currency="BRL", missing=set())

    def respond(request):
        state.calls.append(request.url.params["symbols"])
        if state.failure == "timeout":
            raise httpx.ReadTimeout("synthetic provider failure", request=request)
        if state.failure == "network":
            raise httpx.ConnectError("synthetic provider failure", request=request)
        if state.failure == "json":
            return httpx.Response(200, text="invalid json")
        if state.failure:
            return httpx.Response(state.failure, text="provider body must not be exposed")
        return httpx.Response(200, json={"results": [
            {"requestedSymbol": symbol, "symbol": symbol, "changed": False, "data": {
                "regularMarketPrice": state.price, "currency": state.currency,
                "regularMarketTime": "2026-09-30T13:00:00Z",
            }} for symbol in request.url.params["symbols"].split(",") if symbol not in state.missing
        ]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        service = QuoteService(
            BrapiPriceSource(http, SecretStr("synthetic"), clock=lambda: state.now),
            QuoteCache(100, 1800, clock=lambda: state.now),
        )
        state.service = service
        test_app.dependency_overrides[get_quote_service] = lambda: service
        try:
            yield state
        finally:
            await service.aclose()


async def create_asset(client, ticker="INTERNAL3", **overrides):
    data = {"type": "national_stock", "ticker": ticker, "name": ticker,
            "current_price": "20", "price_provider": "brapi",
            "external_price_id": "BBDC4", "quote_currency": "BRL", **overrides}
    response = await client.post("/admin/assets", json={"assets": [data]},
                                 headers={"X-Admin-Key": "test-admin-key"})
    assert response.status_code == 200, response.text
    return response.json()[0]


async def transact(client, headers, ticker="INTERNAL3", side="buy", quantity="10", price="30"):
    response = await client.post(f"/portfolios/{side}", headers=headers, json={
        "ticker": ticker, "quantity": quantity, "price": price, "transaction_date": "2026-09-30",
    })
    assert response.status_code == 200, response.text
    return response.json()


async def test_market_prices_metadata_cache_and_unchanged_history(client, market):
    headers = await register_and_login(client, "market_user")
    asset = await create_asset(client)
    await transact(client, headers)
    before = (await client.get("/portfolios/transactions", headers=headers)).json()
    started = datetime.now(timezone.utc)
    response = await client.get(PATHS[0], headers=headers)
    assert response.status_code == 200, response.text
    position = response.json()[0]
    assert set(position) == {"asset", "quantity", "average_price", "cost_basis", "market_value",
                             "pnl", "return_percentage", "currency", "quote"}
    assert position["asset"] == {"id": asset["id"], "ticker": "INTERNAL3", "name": "INTERNAL3",
                                  "asset_type": "national_stock", "registered_price": "20.00000000"}
    for key, expected in {"quantity": "10", "average_price": "30", "cost_basis": "300",
                          "market_value": "350", "pnl": "50"}.items():
        assert isinstance(position[key], str)
        assert Decimal(position[key]) == Decimal(expected)
    assert Decimal(position["return_percentage"]) == Decimal("50") / Decimal("300") * 100
    quote = position["quote"]
    assert quote == {"asset_id": asset["id"], "price": "35", "currency": "BRL", "source": "brapi",
                     "quoted_at": "2026-09-30T13:00:00Z", "fetched_at": quote["fetched_at"], "from_cache": False}
    assert started <= datetime.fromisoformat(quote["fetched_at"]) <= datetime.now(timezone.utc)
    summary = (await client.get(PATHS[1], headers=headers)).json()
    assert set(summary) == {"totals_by_currency", "contains_manual_prices", "quotes"}
    assert summary["quotes"] == [{**quote, "from_cache": True}]
    assert summary["contains_manual_prices"] is False
    total = summary["totals_by_currency"][0]
    assert total["currency"] == "BRL" and total["contains_manual_prices"] is False
    assert Decimal(total["total_cost"]) == 300
    assert Decimal(total["total_equity"]) == 350
    assert Decimal(total["total_pnl"]) == 50
    assert total["return_percentage"] == position["return_percentage"]
    assert market.calls == ["BBDC4"]
    assert (await client.get("/portfolios/transactions", headers=headers)).json() == before
    assert (await client.get("/assets", headers=headers)).json()[0]["current_price"] == "20.00000000"
    legacy = (await client.get("/portfolios/positions", headers=headers)).json()[0]
    assert Decimal(legacy["market_value"]) == 200
    assert Decimal(legacy["pnl"]) == -100


async def test_summary_has_one_snapshot_separate_currencies_and_manual_metadata(client, market):
    headers = await register_and_login(client, "currencies")
    await create_asset(client)
    await create_asset(client, "FII", type="real_estate_fund", external_price_id="HGLG11")
    await create_asset(client, "USA", type="international_stock", price_provider="manual",
                       external_price_id=None, quote_currency="USD", current_price="40")
    await create_asset(client, "EURO", type="cryptocurrency", price_provider=None,
                       external_price_id=None, quote_currency="EUR", current_price="15")
    await create_asset(client, "MANUALBR", price_provider="manual", external_price_id=None)
    for ticker in ("INTERNAL3", "FII", "USA", "EURO", "MANUALBR"):
        await transact(client, headers, ticker)
    response = await client.get(PATHS[1], headers=headers)
    assert response.status_code == 200, response.text
    summary = response.json()
    totals = {item["currency"]: item for item in summary["totals_by_currency"]}
    assert list(totals) == ["BRL", "EUR", "USD"]
    assert summary["contains_manual_prices"] is True
    for currency, cost, equity, pnl in [("BRL", 900, 900, 0), ("USD", 300, 400, 100), ("EUR", 300, 150, -150)]:
        assert Decimal(totals[currency]["total_cost"]) == cost
        assert Decimal(totals[currency]["total_equity"]) == equity
        assert Decimal(totals[currency]["total_pnl"]) == pnl
        assert totals[currency]["contains_manual_prices"] is True
    assert sorted(market.calls) == ["BBDC4", "HGLG11"]
    assert len(summary["quotes"]) == 5
    assert all(q["from_cache"] is False for q in summary["quotes"])
    manual = [q for q in summary["quotes"] if q["source"] == "manual"]
    assert len(manual) == 3 and all(q["quoted_at"] is None for q in manual)
    # Independent requests may see a new price after expiry.
    market.now = 1800
    market.price = "36"
    positions = (await client.get(PATHS[0], headers=headers)).json()
    assert all(p["quote"]["price"] == "36" for p in positions if p["quote"]["source"] == "brapi")
    assert all(q["price"] == "35" for q in summary["quotes"] if q["source"] == "brapi")


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("failure", [401, 403, 429, 503, "timeout", "network", "json", "missing", "currency"])
async def test_external_failure_is_complete_safe_503(client, market, path, failure):
    headers = await register_and_login(client, "unavailable")
    asset = await create_asset(client)
    await transact(client, headers)
    if failure == "missing":
        market.missing.add("BBDC4")
    elif failure == "currency":
        market.currency = "USD"
    else:
        market.failure = failure
    response = await client.get(path, headers=headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "Cotação indisponível para um ou mais ativos.", "asset_ids": [asset["id"]]}
    calls = len(market.calls)
    # Provider failure cannot prevent trades, history, catalog or legacy evaluation.
    await transact(client, headers, side="sell", quantity="4", price="32")
    for legacy in ("/portfolios/transactions", "/portfolios/positions", "/portfolios/summary", "/assets"):
        assert (await client.get(legacy, headers=headers)).status_code == 200
    assert len(market.calls) == calls


@pytest.mark.parametrize("path", PATHS)
async def test_expired_cache_cannot_mask_partial_failure(client, market, path):
    headers = await register_and_login(client, "partial")
    await create_asset(client)
    fii = await create_asset(client, "FII", type="real_estate_fund", external_price_id="HGLG11")
    await transact(client, headers)
    await transact(client, headers, "FII")
    assert (await client.get(path, headers=headers)).status_code == 200
    market.now = 1800
    market.missing.add("HGLG11")
    response = await client.get(path, headers=headers)
    assert response.status_code == 503
    assert response.json()["asset_ids"] == [fii["id"]]
    assert sorted(market.calls) == ["BBDC4", "BBDC4", "HGLG11", "HGLG11"]


@pytest.mark.parametrize("path", PATHS)
async def test_all_missing_currencies_fail_before_external_calls(client, market, path):
    headers = await register_and_login(client, "missing_currency")
    await create_asset(client)
    await transact(client, headers)
    ids = []
    for ticker in ("CRYPTO1", "CRYPTO2"):
        asset = await create_asset(client, ticker, type="cryptocurrency", price_provider=None,
                                   external_price_id=None, quote_currency=None)
        ids.append(asset["id"])
        await transact(client, headers, ticker)
    response = await client.get(path, headers=headers)
    assert response.status_code == 422
    assert response.json() == {"detail": "Configuração de cotação inválida para um ou mais ativos.", "asset_ids": ids}
    assert market.calls == []


async def test_empty_closed_and_other_users_positions_do_not_fetch_quotes(client, market):
    owner = await register_and_login(client, "owner")
    other = await register_and_login(client, "other")
    await create_asset(client)
    await transact(client, owner)
    assert (await client.get(PATHS[0], headers=other)).json() == []
    assert (await client.get(PATHS[1], headers=other)).json() == {
        "totals_by_currency": [], "contains_manual_prices": False, "quotes": [],
    }
    await transact(client, owner, side="sell", quantity="10")
    # Closed positions with missing configuration are also excluded.
    await create_asset(client, "OLD", type="cryptocurrency", price_provider=None,
                       external_price_id=None, quote_currency=None)
    await transact(client, owner, "OLD")
    await transact(client, owner, "OLD", side="sell")
    assert (await client.get(PATHS[0], headers=owner)).json() == []
    assert (await client.get(PATHS[1], headers=owner)).json()["totals_by_currency"] == []
    assert market.calls == []


async def test_all_manual_asset_classes_and_weighted_average(client, market, legacy_http_examples):
    headers = await register_and_login(client, "manual_classes")
    for data in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]:
        await create_asset(client, **{**data, "price_provider": "manual", "external_price_id": None,
                                      "quote_currency": "USD" if data["type"] == "international_stock" else "BRL"})
        await transact(client, headers, data["ticker"], quantity="10", price="30")
        await transact(client, headers, data["ticker"], quantity="5", price="60")
        await transact(client, headers, data["ticker"], side="sell", quantity="3", price="70")
    response = await client.get(PATHS[0], headers=headers)
    assert response.status_code == 200, response.text
    assert len(response.json()) == 6
    for p in response.json():
        assert Decimal(p["average_price"]) == 40
        assert Decimal(p["quantity"]) == 12
        assert Decimal(p["cost_basis"]) == 480
        assert p["quote"]["source"] == "manual"
        assert p["quote"]["price"] == p["asset"]["registered_price"]
    assert market.calls == []


@pytest.mark.parametrize("path", PATHS)
async def test_v2_requires_authentication(client, market, path):
    assert (await client.get(path)).status_code == 401
    assert (await client.get(path, headers={"Authorization": "Bearer invalid"})).status_code == 401
    assert market.calls == []


async def test_programming_errors_are_not_converted_to_availability_errors(client, market, monkeypatch):
    headers = await register_and_login(client, "programming_error")
    await create_asset(client)
    await transact(client, headers)
    monkeypatch.setattr(market.service, "get_quotes", AsyncMock(side_effect=RuntimeError("synthetic bug")))
    with pytest.raises(RuntimeError, match="synthetic bug"):
        await client.get(PATHS[0], headers=headers)


async def test_invalid_persisted_provider_mapping_returns_422(client, market, async_db):
    headers = await register_and_login(client, "mapping")
    asset = await create_asset(client)
    await transact(client, headers)
    model = await async_db.scalar(select(AssetModel).where(AssetModel.ticker == "INTERNAL3"))
    model.external_price_id = None
    await async_db.commit()
    response = await client.get(PATHS[0], headers=headers)
    assert response.status_code == 422
    assert response.json()["asset_ids"] == [asset["id"]]
    assert market.calls == []


async def test_all_unavailable_asset_ids_are_returned(client, market):
    headers = await register_and_login(client, "all_unavailable")
    stock = await create_asset(client)
    fii = await create_asset(client, "FII", type="real_estate_fund", external_price_id="HGLG11")
    await transact(client, headers)
    await transact(client, headers, "FII")
    market.failure = 503
    response = await client.get(PATHS[1], headers=headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "Cotação indisponível para um ou mais ativos.",
                               "asset_ids": [stock["id"], fii["id"]]}


async def test_missing_token_returns_503_without_external_http(client, market, test_app, monkeypatch):
    headers = await register_and_login(client, "missing_token")
    asset = await create_asset(client)
    await transact(client, headers)
    # Exercise the real lifespan dependency with its empty test token.
    test_app.dependency_overrides.pop(get_quote_service)
    monkeypatch.setattr(test_app.state.quote_service._source, "_token", SecretStr(""))
    response = await client.get(PATHS[0], headers=headers)
    assert response.status_code == 503
    assert response.json()["asset_ids"] == [asset["id"]]
    assert market.calls == []


async def test_shared_external_symbol_preserves_internal_ids_and_decimal_precision(client, market):
    headers = await register_and_login(client, "precision")
    first = await create_asset(client)
    second = await create_asset(client, "ALIAS3")
    for ticker in ("INTERNAL3", "ALIAS3"):
        await transact(client, headers, ticker, quantity="0.12345678")
    market.price = "35.123456789123456789"
    response = await client.get(PATHS[0], headers=headers)
    assert response.status_code == 200, response.text
    assert [p["quote"]["asset_id"] for p in response.json()] == [first["id"], second["id"]]
    for p in response.json():
        assert p["quote"]["price"] == market.price
        assert Decimal(p["market_value"]) == Decimal("0.12345678") * Decimal(market.price)
    assert market.calls == ["BBDC4"]
