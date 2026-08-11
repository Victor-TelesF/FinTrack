from uuid import uuid4


def register_and_login(client, user_name):
    client.post(
        "/auth/register",
        json={"user_name": user_name, "password": "senha123"},
    )
    response = client.post(
        "/auth/login",
        json={"user_name": user_name, "password": "senha123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_stock(client, headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    response = client.post(
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


def test_buy_sell_and_list_transactions(client, monkeypatch):
    headers = register_and_login(client, "portfolio_user")
    create_stock(client, headers, monkeypatch)
    portfolio = client.get("/portfolios", headers=headers).json()[0]
    portfolio_id = portfolio["id_portfolio"]

    buy = client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    sell = client.post(
        "/portfolios/sell",
        json={
            "ticker": "ABCD3",
            "quantity": "4",
            "price": "22.00",
            "transaction_date": "2026-02-05",
        },
        headers=headers,
    )
    transactions = client.get(
        "/portfolios/transactions",
        headers=headers,
    )

    assert buy.status_code == 200
    assert sell.status_code == 200, sell.text
    assert transactions.status_code == 200
    assert len(transactions.json()) == 2
    assert transactions.json()[0]["transaction_type"] == "buy"
    assert transactions.json()[1]["transaction_type"] == "sell"


def test_positions_after_same_day_sell(client, monkeypatch):
    headers = register_and_login(client, "same_day_position_user")
    create_stock(client, headers, monkeypatch)

    for quantity, price in (("10", "18.50"), ("5", "19.00")):
        response = client.post(
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

    sell = client.post(
        "/portfolios/sell",
        json={
            "ticker": "ABCD3",
            "quantity": "4",
            "price": "22.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    positions = client.get("/portfolios/positions", headers=headers)

    assert sell.status_code == 200, sell.text
    assert positions.status_code == 200, positions.text
    assert positions.json()[0]["quantity"] == "11.00000000"


def test_sell_above_position_returns_validation_error(client, monkeypatch):
    headers = register_and_login(client, "insufficient_user")
    create_stock(client, headers, monkeypatch)
    portfolio_id = client.get("/portfolios", headers=headers).json()[0]["id_portfolio"]

    response = client.post(
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


def test_unknown_portfolio_returns_not_found(client):
    headers = register_and_login(client, "missing_portfolio_user")

    response = client.get(f"/portfolios/{uuid4()}/transactions", headers=headers)

    assert response.status_code == 404


def test_user_cannot_access_other_user_transactions(client, monkeypatch):
    user_a_headers = register_and_login(client, "user_a")
    user_b_headers = register_and_login(client, "user_b")

    portfolio_b = client.get("/portfolios", headers=user_b_headers).json()[0]
    response = client.get(f"/portfolios/{portfolio_b['id_portfolio']}/transactions", headers=user_a_headers)

    assert response.status_code == 404


def test_buy_sell_with_unknown_ticker_returns_validation_error(client, monkeypatch):
    headers = register_and_login(client, "ticker_user")

    response_buy = client.post(
        "/portfolios/buy",
        json={
            "ticker": "UNKNOWN",
            "quantity": "10",
            "price": "15.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_sell = client.post(
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


def test_buy_with_invalid_quantity_or_price_returns_validation_error(client, monkeypatch):
    headers = register_and_login(client, "invalid_transaction_user")
    create_stock(client, headers, monkeypatch)

    response_quantity_zero = client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "0",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_quantity_negative = client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "-1",
            "price": "18.50",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_price_zero = client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "0",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )
    response_price_negative = client.post(
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


def test_positions_and_summary_are_calculated_from_transactions(client, monkeypatch):
    from decimal import Decimal

    headers = register_and_login(client, "summary_user")
    create_stock(client, headers, monkeypatch)
    client.post(
        "/portfolios/buy",
        json={
            "ticker": "ABCD3",
            "quantity": "10",
            "price": "18.00",
            "transaction_date": "2026-01-05",
        },
        headers=headers,
    )

    positions = client.get("/portfolios/positions", headers=headers)
    summary = client.get("/portfolios/summary", headers=headers)

    assert positions.status_code == 200
    assert positions.json()[0]["quantity"] == "10.00000000"
    assert Decimal(positions.json()[0]["cost_basis"]) == Decimal("180")
    assert Decimal(positions.json()[0]["market_value"]) == Decimal("200")
    assert Decimal(positions.json()[0]["pnl"]) == Decimal("20")
    assert summary.status_code == 200
    assert Decimal(summary.json()["total_cost"]) == Decimal("180")
    assert Decimal(summary.json()["total_equity"]) == Decimal("200")
    assert Decimal(summary.json()["total_pnl"]) == Decimal("20")