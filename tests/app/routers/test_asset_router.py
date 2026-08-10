def register_and_login(client):
    client.post(
        "/auth/register",
        json={"user_name": "asset_user", "password": "senha123"},
    )
    response = client.post(
        "/auth/login",
        json={"user_name": "asset_user", "password": "senha123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_asset_catalog_requires_authentication(client):
    response = client.get("/assets")

    assert response.status_code == 401


def test_admin_upserts_cdb_and_user_lists_assets(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-admin-key")
    headers = register_and_login(client)
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
    created = client.post(
        "/admin/assets",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    listed = client.get("/assets", headers=headers)

    assert created.status_code == 200
    assert created.json()[0]["ticker"] == "CDBFT"
    assert listed.status_code == 200
    assert listed.json()[0]["ticker"] == "CDBFT"


def test_admin_asset_upsert_requires_admin_key(client):
    response = client.post(
        "/admin/assets",
        json={"assets": []},
    )

    assert response.status_code == 403


def test_get_unknown_asset_returns_not_found(client):
    headers = register_and_login(client)

    response = client.get(
        "/assets/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404