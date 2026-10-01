from decimal import Decimal

import pytest

from app.config import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    return {"X-Admin-Key": "test-admin-key"}


def item(**changes):
    return {"type": "national_stock", "name": "Petrobras", "ticker": "PETR4",
            "current_price": "35.12345678", **changes}


async def post(client, headers, *items):
    return await client.post("/admin/assets", json={"assets": items}, headers=headers)


@pytest.mark.parametrize("asset_type,ticker", [("national_stock", "PETR4"), ("real_estate_fund", "HGLG11")])
async def test_configure_provider_preserve_on_legacy_update_and_clear(client, admin_headers, asset_type, ticker):
    payload = item(type=asset_type, ticker=ticker, quote_currency="BRL",
                   price_provider="brapi", external_price_id=ticker)
    response = await post(client, admin_headers, payload)
    assert response.status_code == 200, response.text
    before = response.json()[0]
    assert {key: before[key] for key in ("quote_currency", "price_provider", "external_price_id")} == {
        "quote_currency": "BRL", "price_provider": "brapi", "external_price_id": ticker,
    }
    response = await post(client, admin_headers, item(type=asset_type, ticker=ticker, name="Updated"))
    assert response.status_code == 200
    assert response.json()[0] == {**before, "name": "Updated"}
    response = await post(client, admin_headers, item(type=asset_type, ticker=ticker,
                                                    price_provider="manual", external_price_id=None))
    assert response.status_code == 200
    assert response.json()[0] == {**before, "price_provider": "manual", "external_price_id": None}


@pytest.mark.parametrize("changes", [
    {"quote_currency": "USD"},
    {"quote_currency": None},
    {"type": "international_stock", "quote_currency": "BRL"},
    {"price_provider": "unknown"},
    {"price_provider": "brapi"},
    {"price_provider": "brapi", "external_price_id": " "},
    {"price_provider": "brapi", "external_price_id": "PETR4,VALE3"},
    {"price_provider": "brapi", "external_price_id": "petr4"},
    {"external_price_id": "PETR4"},
    {"price_provider": "manual", "external_price_id": "PETR4"},
    {"type": "real_estate_fund", "price_provider": "brapi", "external_price_id": "HGLG11"},
    {"type": "cryptocurrency", "quote_currency": "BRL", "price_provider": "brapi", "external_price_id": "BTC"},
    {"type": "international_stock", "price_provider": "brapi", "external_price_id": "AAPL"},
    {"quote_currency": "XYZ"},
    {"external_price_id": "X" * 101},
])
async def test_invalid_metadata_rolls_back_whole_batch(client, admin_headers, async_db, changes):
    from sqlalchemy import select
    from app.models import AssetModel

    response = await post(client, admin_headers, item(ticker="VALID3"), item(**changes))
    assert response.status_code == 422, response.text
    assert list(await async_db.scalars(select(AssetModel))) == []


@pytest.mark.parametrize("initial,requested", [("BRL", "USD"), ("USD", None), (None, "BRL")])
async def test_currency_is_locked_even_after_full_sale(client, admin_headers, initial, requested):
    payload = item(type="cryptocurrency", ticker="BTC", quote_currency=initial)
    created = await post(client, admin_headers, payload)
    assert created.status_code == 200
    original = created.json()[0]
    await client.post("/auth/register", json={"user_name": "currency_owner", "password": "senha123"})
    login = await client.post("/auth/login", json={"user_name": "currency_owner", "password": "senha123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    transaction = {"ticker": "BTC", "quantity": "2", "price": "25.98765432", "transaction_date": "2026-10-01"}
    for action in ("buy", "sell"):
        response = await client.post(f"/portfolios/{action}", json=transaction, headers=headers)
        assert response.status_code == 200, response.text
    history = (await client.get("/portfolios/transactions", headers=headers)).json()
    response = await post(client, admin_headers, item(ticker="NEW3"),
                          {**payload, "quote_currency": requested, "current_price": "99"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Moeda de ativo com transações só pode ser alterada por migração específica"}
    assert (await client.get("/assets", headers=headers)).json() == [original]
    assert (await client.get("/portfolios/transactions", headers=headers)).json() == history
    assert all(Decimal(row["price"]) == Decimal(transaction["price"]) for row in history)
    assert (await post(client, admin_headers, {**payload, "current_price": "99"})).status_code == 200


async def test_currency_can_change_without_transactions_and_type_cannot(client, admin_headers):
    payload = item(type="cryptocurrency", ticker="BTC", quote_currency="BRL")
    created = (await post(client, admin_headers, payload)).json()[0]
    response = await post(client, admin_headers, {**payload, "quote_currency": "USD"})
    assert response.status_code == 200
    assert response.json()[0] == {**created, "quote_currency": "USD"}
    response = await post(client, admin_headers, {**payload, "type": "national_stock"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Tipo de ativo existente não pode ser alterado"}
