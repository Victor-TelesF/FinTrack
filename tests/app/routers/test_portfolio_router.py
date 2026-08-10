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