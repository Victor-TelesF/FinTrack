from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


async def register_and_login(client, user_name):
    await client.post(
        "/auth/register",
        json={"user_name": user_name, "password": "senha123"},
    )
    response = await client.post(
        "/auth/login",
        json={"user_name": user_name, "password": "senha123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_stock(client, headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    response = await client.post(
        "/admin/assets",
        json={"assets": [{
            "type": "national_stock",
            "name": "Empresa",
            "ticker": "ABCD3",
            "current_price": "20.00",
        }]},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 200


async def test_buy_sell_and_list_transactions(client, monkeypatch):
    headers = await register_and_login(client, "portfolio_user")
    await create_stock(client, headers, monkeypatch)
    portfolio = (await client.get("/portfolios", headers=headers)).json()[0]
    portfolio_id = portfolio["id_portfolio"]

    buy = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    sell = await client.post(
        "/portfolios/sell",
        json={
            "ticker": "ABCD3",
            "quantity": "4",
            "price": "22.00",
            "transaction_date": "2026-02-05",
        },
        headers=headers,
    )
    transactions = await client.get(
        "/portfolios/transactions",
        headers=headers,
    )

    assert buy.status_code == 200
    assert sell.status_code == 200, sell.text
    assert transactions.status_code == 200
    assert len(transactions.json()) == 2
    assert transactions.json()[0]["transaction_type"] == "buy"
    assert transactions.json()[1]["transaction_type"] == "sell"


async def test_positions_after_same_day_sell(client, monkeypatch):
    headers = await register_and_login(client, "same_day_position_user")
    await create_stock(client, headers, monkeypatch)

    # The database sequence is shared across portfolios, not a position index.
    other_headers = await register_and_login(client, "other_position_user")
    for _ in range(2):
        response = await client.post(
            "/portfolios/buy",
            json={
                "ticker": "ABCD3",
                "quantity": "1",
                "price": "20.00",
                "transaction_date": "2026-01-05",
            },
            headers=other_headers,
        )
        assert response.status_code == 200, response.text

    for quantity, price in (("10", "18.50"), ("5", "19.00")):
        response = await client.post(
            "/portfolios/buy",
            json={
                "ticker": "ABCD3",
                "quantity": quantity,
                "price": price,
                "transaction_date": "2026-01-05",
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text

    sell = await client.post(
        "/portfolios/sell",
        json={
            "ticker": "ABCD3",
            "quantity": "4",
            "price": "22.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    positions = await client.get("/portfolios/positions", headers=headers)

    assert sell.status_code == 200, sell.text
    assert positions.status_code == 200, positions.text
    assert positions.json()[0]["quantity"] == "11.00000000"


async def test_sell_above_position_returns_validation_error(client, monkeypatch):
    headers = await register_and_login(client, "insufficient_user")
    await create_stock(client, headers, monkeypatch)
    portfolio_id = (await client.get("/portfolios", headers=headers)).json()[0]["id_portfolio"]

    response = await client.post(
        "/portfolios/sell",
        json={
            "ticker": "ABCD3",
            "quantity": "1",
            "price": "22.00",
            "transaction_date": "2026-02-05",
        },
        headers=headers,
    )

    assert response.status_code == 422


async def test_unknown_portfolio_returns_not_found(client):
    headers = await register_and_login(client, "missing_portfolio_user")

    response = await client.get(f"/portfolios/{uuid4()}/transactions", headers=headers)

    assert response.status_code == 404


async def test_user_cannot_access_other_user_transactions(client, monkeypatch):
    user_a_headers = await register_and_login(client, "user_a")
    user_b_headers = await register_and_login(client, "user_b")

    portfolio_b = (await client.get("/portfolios", headers=user_b_headers)).json()[0]
    response = await client.get(f"/portfolios/{portfolio_b['id_portfolio']}/transactions", headers=user_a_headers)

    assert response.status_code == 404


async def test_buy_sell_with_unknown_ticker_returns_validation_error(client, monkeypatch):
    headers = await register_and_login(client, "ticker_user")

    response_buy = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "UNKNOWN",
            "quantity": "10",
            "price": "15.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_sell = await client.post(
        "/portfolios/sell",
        json={
            "ticker": "UNKNOWN",
            "quantity": "1",
            "price": "15.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )

    assert response_buy.status_code == 422
    assert response_sell.status_code == 422


async def test_buy_with_invalid_quantity_or_price_returns_validation_error(client, monkeypatch):
    headers = await register_and_login(client, "invalid_transaction_user")
    await create_stock(client, headers, monkeypatch)

    response_quantity_zero = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "0",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_quantity_negative = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "-1",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_price_zero = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "0",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_price_negative = await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "-5.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )

    assert response_quantity_zero.status_code == 422
    assert response_quantity_negative.status_code == 422
    assert response_price_zero.status_code == 422
    assert response_price_negative.status_code == 422


async def test_positions_and_summary_are_calculated_from_transactions(client, monkeypatch):
    from decimal import Decimal

    headers = await register_and_login(client, "summary_user")
    await create_stock(client, headers, monkeypatch)
    await client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "18.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )

    positions = await client.get("/portfolios/positions", headers=headers)
    summary = await client.get("/portfolios/summary", headers=headers)

    assert positions.status_code == 200
    assert positions.json()[0]["quantity"] == "10.00000000"
    assert Decimal(positions.json()[0]["cost_basis"]) == Decimal("180")
    assert Decimal(positions.json()[0]["market_value"]) == Decimal("200")
    assert Decimal(positions.json()[0]["pnl"]) == Decimal("20")
    assert summary.status_code == 200
    assert Decimal(summary.json()["total_cost"]) == Decimal("180")
    assert Decimal(summary.json()["total_equity"]) == Decimal("200")
    assert Decimal(summary.json()["total_pnl"]) == Decimal("20")


async def test_portfolio_legacy_contracts(client, monkeypatch, legacy_http_examples):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    headers = await register_and_login(client, "legacy_portfolio")
    ids = {}

    def normalize(actual, expected):
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys()
            return {
                key: ids.setdefault(value, actual[key])
                if key in {"id", "id_transaction", "id_portfolio"}
                else normalize(actual[key], value)
                for key, value in expected.items()
            }
        if isinstance(expected, list):
            assert len(actual) == len(expected)
            return [normalize(a, e) for a, e in zip(actual, expected)]
        return expected

    names = ["admin_catalog", "portfolios", "buy", "positions_after_buy", "summary_after_buy",
             "same_day_sell", "history", "portfolio_history", "positions_after_sell",
             "summary_after_sell", "insufficient_balance", "full_sale", "empty_positions", "empty_summary"]
    for name in names:
        example = legacy_http_examples[name]
        request = example["request"]
        path = request["path"]
        for old_id, new_id in ids.items():
            path = path.replace(old_id, new_id)
        response = await client.request(
            request["method"], path, json=request.get("json"),
            headers={**headers, "X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == example["response"]["status_code"], (name, response.text)
        actual = response.json()
        if name == "admin_catalog":
            actual = [{key: value for key, value in item.items()
                       if key not in {"price_provider", "external_price_id", "quote_currency"}}
                      for item in actual]
        assert actual == normalize(actual, example["response"]["json"]), name


async def test_concurrent_http_sales_preserve_balance(client, monkeypatch):
    import asyncio
    from decimal import Decimal

    headers = await register_and_login(client, "concurrent_http")
    await create_stock(client, headers, monkeypatch)
    payload = {"ticker": "ABCD3", "quantity": "10", "price": "30", "transaction_date": "2026-09-25"}
    assert (await client.post("/portfolios/buy", json=payload, headers=headers)).status_code == 200
    payload["quantity"] = "7"
    responses = await asyncio.gather(*[
        client.post("/portfolios/sell", json=payload, headers=headers) for _ in range(2)
    ])
    assert sorted(response.status_code for response in responses) == [200, 422]
    rejected = next(response for response in responses if response.status_code == 422)
    assert rejected.json() == {"detail": "Não é possivel vender mais do que possui"}
    positions = await client.get("/portfolios/positions", headers=headers)
    assert Decimal(positions.json()[0]["quantity"]) == Decimal("3")
    history = await client.get("/portfolios/transactions", headers=headers)
    assert len(history.json()) == 2


async def test_openapi_preserves_marco_a_except_additive_catalog_metadata(test_app):
    import json
    from pathlib import Path

    reference = Path(__file__).resolve().parents[2] / "contracts" / "openapi-marco-a.json"
    # Keep the snapshot intact; allow only catalog metadata and the two v2 reads.
    current = json.loads(json.dumps(test_app.openapi()))
    schemas = current["components"]["schemas"]
    for path, schema in (("positions", "PositionValuationRead"), ("summary", "PortfolioValuationRead")):
        route = current["paths"].pop(f"/api/v2/portfolios/{path}")
        assert set(route) == {"get"}
        operation = route["get"]
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]
        response = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert (response.get("items", response))["$ref"] == f"#/components/schemas/{schema}"
        for status in ("422", "503"):
            assert operation["responses"][status]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ValuationErrorRead",
            }
    for name in ("PositionValuationRead", "PortfolioValuationRead", "CurrencyTotalRead",
                 "ValuationAssetRead", "QuoteRead", "ValuationErrorRead"):
        schemas.pop(name)
    catalog = schemas.pop("AssetQuoteCatalogRead")
    assert catalog["required"] == schemas["AssetCatalogRead"]["required"]
    for field in ("price_provider", "external_price_id", "quote_currency"):
        assert catalog["properties"].pop(field) == schemas["AdminAssetItem"]["properties"].pop(field)
    catalog["title"] = "AssetCatalogRead"
    catalog.pop("description")
    assert catalog == schemas["AssetCatalogRead"]
    for path, method in (("/admin/assets", "post"), ("/assets", "get"), ("/assets/{asset_id}", "get")):
        response = current["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        ref = response["items"] if "items" in response else response
        assert ref["$ref"] == "#/components/schemas/AssetQuoteCatalogRead"
        ref["$ref"] = "#/components/schemas/AssetCatalogRead"
    assert current == json.loads(reference.read_text())
