"""Small controlled comparison; latency is evidence, never a timing assertion.

Run with pytest -q -s tests/app/routers/test_valuation_measurements.py.
The provider returns immediately via MockTransport; this is not a load test.
"""
import json
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import event

from tests.app.routers.test_portfolio_router import register_and_login
from tests.app.routers.test_portfolio_v2_router import create_asset, market, transact

pytestmark = pytest.mark.asyncio


async def test_sql_and_provider_counts_with_cold_and_warm_cache(client, market, async_engine):
    headers = await register_and_login(client, "measurements")
    await create_asset(client)
    await create_asset(client, "FII", type="real_estate_fund", external_price_id="HGLG11")
    for ticker in ("INTERNAL3", "FII"):
        await transact(client, headers, ticker)
    sql_count = 0

    def count_sql(*args):
        nonlocal sql_count
        sql_count += 1

    # Warm the DB connection/statement caches before comparing request work.
    assert (await client.get("/portfolios/summary", headers=headers)).status_code == 200
    event.listen(async_engine.sync_engine, "before_cursor_execute", count_sql)
    measurements = []
    try:
        for path in ("positions", "summary"):
            for _ in range(5):
                market.now += 1800  # Expire the controlled cache without real sleeps.
                for variant, prefix, expected_calls in (
                    ("legacy", "/portfolios", 0),
                    ("cold", "/api/v2/portfolios", 2),
                    ("warm", "/api/v2/portfolios", 0),
                ):
                    sql_count = 0
                    calls_before = len(market.calls)
                    started = perf_counter()
                    response = await client.get(f"{prefix}/{path}", headers=headers)
                    elapsed_ms = (perf_counter() - started) * 1000
                    assert response.status_code == 200
                    provider_calls = len(market.calls) - calls_before
                    assert provider_calls == expected_calls
                    # User, portfolio, and all transactions/assets in one joined load.
                    assert sql_count == 3
                    if variant != "legacy":
                        body = response.json()
                        quotes = [p["quote"] for p in body] if path == "positions" else body["quotes"]
                        assert len(quotes) == 2
                        assert all(q["from_cache"] == (variant == "warm") for q in quotes)
                    measurements.append({"path": path, "variant": variant, "sql": sql_count,
                                         "provider": provider_calls, "ms": elapsed_ms})
    finally:
        event.remove(async_engine.sync_engine, "before_cursor_execute", count_sql)
    for path in ("positions", "summary"):
        for variant in ("legacy", "cold", "warm"):
            rows = [row for row in measurements if row["path"] == path and row["variant"] == variant]
            print(json.dumps({"path": path, "variant": variant, "samples": len(rows),
                              "sql_per_request": rows[0]["sql"], "provider_calls": rows[0]["provider"],
                              "median_ms": round(median(row["ms"] for row in rows), 3)}))
