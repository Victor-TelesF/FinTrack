"""HTTP smoke check inside the disposable production-image validation stack.

Creates synthetic data. Run only via docker-compose.validation.yml, never on a
real deployment. No test dependencies or external market requests are needed.
"""
import importlib.util
import json
import os
from decimal import Decimal
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.config import settings


def main():
    if settings.POSTGRES_DB != "release_test" or settings.BRAPI_TOKEN.get_secret_value():
        raise RuntimeError("Use only the isolated release_test stack with an empty BRAPI_TOKEN")
    assert os.getuid() != 0, "Production application must run as a non-root user"
    assert all(importlib.util.find_spec(name) is None for name in (
        "pytest", "pytest_asyncio", "asgi_lifespan",
    ))
    import psycopg
    from sqlalchemy.ext.asyncio import AsyncSession
    assert psycopg.AsyncConnection and AsyncSession
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "9d2a6c4e8f10"
    finally:
        engine.dispose()

    suffix = uuid4().hex[:10].upper()
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15) as client:
        def request(method, path, *, status=200, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == status, (method, path, response.status_code)
            return response.json()

        request("GET", "/openapi.json")
        request("GET", "/api/v2/portfolios/summary", status=401)
        credentials = {"user_name": f"release_{suffix}", "password": "synthetic-password"}
        request("POST", "/auth/register", json=credentials)
        token = request("POST", "/auth/login", json=credentials)["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        assert request("GET", "/api/v2/portfolios/positions") == []
        tickers = [f"BR{suffix}", f"US{suffix}"]
        assets = request("POST", "/admin/assets", headers={"X-Admin-Key": settings.ADMIN_KEY}, json={
            "assets": [{"type": kind, "ticker": ticker, "name": ticker,
                        "current_price": "35", "quote_currency": currency, "price_provider": "manual"}
                       for ticker, kind, currency in zip(tickers,
                           ("national_stock", "international_stock"), ("BRL", "USD"))],
        })
        for ticker in tickers:
            request("POST", "/portfolios/buy", json={
                "ticker": ticker, "quantity": "10", "price": "30", "transaction_date": "2026-10-01",
            })
        request("POST", "/portfolios/sell", json={
            "ticker": tickers[0], "quantity": "2", "price": "32", "transaction_date": "2026-10-01",
        })
        history = request("GET", "/portfolios/transactions")
        assert len(history) == 3
        positions = request("GET", "/api/v2/portfolios/positions")
        assert len(positions) == 2
        assert all(p["quote"]["source"] == "manual" and p["quote"]["quoted_at"] is None for p in positions)
        summary = request("GET", "/api/v2/portfolios/summary")
        assert summary["contains_manual_prices"] is True
        assert [(t["currency"], Decimal(t["total_cost"]), Decimal(t["total_equity"]))
                for t in summary["totals_by_currency"]] == [("BRL", 240, 280), ("USD", 300, 350)]
        assert len(request("GET", "/portfolios/positions")) == 2
        request("GET", "/portfolios/summary")
        assert request("GET", "/portfolios/transactions") == history
        assert len(request("GET", "/assets")) >= 2
        cors = client.options("/api/v2/portfolios/summary", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        })
        assert cors.status_code == 200
        assert cors.headers["access-control-allow-origin"] == "http://localhost:3000"

        # Empty token fails before any network call, through the real lifespan service.
        request("POST", "/admin/assets", headers={"X-Admin-Key": settings.ADMIN_KEY}, json={"assets": [{
            "type": "national_stock", "ticker": tickers[0], "name": tickers[0], "current_price": "35",
            "quote_currency": "BRL", "price_provider": "brapi", "external_price_id": "BBDC4",
        }]})
        for path in ("positions", "summary"):
            error = request("GET", f"/api/v2/portfolios/{path}", status=503)
            assert error == {"detail": "Cotação indisponível para um ou mais ativos.", "asset_ids": [assets[0]["id"]]}
        assert request("GET", "/portfolios/transactions") == history
        request("GET", "/portfolios/summary")
    print(json.dumps({"result": "passed", "migration": "9d2a6c4e8f10", "dev_dependencies": False,
                      "flow": "register/login/catalog/buy/sell/legacy/v2/history/CORS/503",
                      "external_calls": 0}))


if __name__ == "__main__":
    main()
