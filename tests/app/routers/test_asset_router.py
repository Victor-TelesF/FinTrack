import pytest

pytestmark = pytest.mark.asyncio


async def register_and_login(client):
    await client.post(
        "/auth/register",
        json={"user_name": "asset_user", "password": "senha123"},
    )
    response = await client.post(
        "/auth/login",
        json={"user_name": "asset_user", "password": "senha123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_asset_catalog_requires_authentication(client):
    response = await client.get("/assets")

    assert response.status_code == 401


async def test_cors_allows_configured_frontend_origin(client):
    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_admin_upserts_cdb_and_user_lists_assets(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    headers = await register_and_login(client)
    payload = {
        "name": "CDB Banco FinTrack",
        "ticker": "CDBFT",
        "current_price": "100.00",
        "fgc_covered": True,
        "liquidity_type": "diaria",
        "index_type": "cdi",
        "maturity_date": "2030-01-01",
        "rate": "0.12",
    }

    payload = {"assets": [{"type": "cdb", **payload}]}
    created = await client.post(
        "/admin/assets",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    listed = await client.get("/assets", headers=headers)

    assert created.status_code == 200
    assert created.json()[0]["ticker"] == "CDBFT"
    assert created.json()[0]["asset_type"] == "cdb"
    assert listed.status_code == 200
    assert listed.json()[0]["ticker"] == "CDBFT"


async def test_admin_asset_upsert_requires_admin_key(client):
    response = await client.post(
        "/admin/assets",
        json={"assets": []},
    )

    assert response.status_code == 403


async def test_admin_asset_upsert_with_invalid_key_returns_forbidden(client):
    response = await client.post(
        "/admin/assets",
        json={"assets": []},
        headers={"X-Admin-Key": "invalid-key"},
    )

    assert response.status_code == 403


async def test_get_unknown_asset_returns_not_found(client):
    headers = await register_and_login(client)

    response = await client.get(
        "/assets/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404


async def test_all_asset_types_match_baseline_on_create_list_and_get(
    client, monkeypatch, legacy_http_examples
):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    headers = await register_and_login(client)
    baseline = legacy_http_examples["admin_catalog"]
    created = await client.post(
        "/admin/assets",
        json=baseline["request"]["json"],
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert created.status_code == 200, created.text
    assert len(created.json()) == 6

    for actual, expected in zip(created.json(), baseline["response"]["json"], strict=True):
        # Only the three additive catalog fields differ from the Marco A contract.
        assert {k: v for k, v in actual.items() if k not in {"id", "price_provider", "external_price_id", "quote_currency"}} == {
            k: v for k, v in expected.items() if k != "id"
        }
        assert actual["price_provider"] is None
        assert actual["external_price_id"] is None
        assert actual["quote_currency"] == {
            "national_stock": "BRL", "international_stock": "USD",
        }.get(actual["asset_type"])
        retrieved = await client.get(f"/assets/{actual['id']}", headers=headers)
        assert retrieved.status_code == 200
        assert retrieved.json() == actual

    listed = await client.get("/assets", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == sorted(created.json(), key=lambda item: item["ticker"])


async def test_admin_updates_all_asset_types_without_changing_ids(
    client, monkeypatch, legacy_http_examples
):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    headers = await register_and_login(client)
    payload = legacy_http_examples["admin_catalog"]["request"]["json"]
    admin_headers = {"X-Admin-Key": "test-admin-key"}
    created = await client.post("/admin/assets", json=payload, headers=admin_headers)
    assert created.status_code == 200

    for item in payload["assets"]:
        item["name"] += " atualizado"
        item["current_price"] = "123.45678901"
        if "rate" in item:
            item["rate"] = "0.13579135"
    updated = await client.post("/admin/assets", json=payload, headers=admin_headers)
    assert updated.status_code == 200, updated.text
    for before, after in zip(created.json(), updated.json(), strict=True):
        expected = {**before, "name": before["name"] + " atualizado", "current_price": "123.45678901"}
        if before["rate"] is not None:
            expected["rate"] = "0.13579135"
        assert after == expected

    listed = await client.get("/assets", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == sorted(updated.json(), key=lambda item: item["ticker"])
