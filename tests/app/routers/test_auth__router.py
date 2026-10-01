from uuid import UUID, uuid4

import pytest

from app.dependencies import get_token_handler
from app.models import PortfolioModel

pytestmark = pytest.mark.asyncio


async def test_register_creates_user(client):
    response = await client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    assert response.status_code == 200
    assert response.json()["user_name"] == "victor"


async def test_register_duplicate_user_name_raises_conflict(client):
    await client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = await client.post("/auth/register", json={
        "user_name": "victor",
        "password": "outrasenha456",
    })

    assert response.status_code == 409


async def test_login_with_correct_credentials_returns_token(client):
    await client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = await client.post("/auth/login", json={
        "user_name": "victor",
        "password": "senha123",
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


async def test_login_with_nonexistent_user_raises_invalid_credentials(client):
    response = await client.post("/auth/login", json={
        "user_name": "nao_existe",
        "password": "qualquersenha",
    })

    assert response.status_code == 401


from app.routers.auth_router import reset_rate_limit_state


async def test_login_with_wrong_password_raises_invalid_credentials(client):
    await client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = await client.post("/auth/login", json={
        "user_name": "victor",
        "password": "senhaerrada",
    })

    assert response.status_code == 401


async def test_login_with_different_usernames_hits_rate_limit_by_ip(client):
    reset_rate_limit_state()
    for i in range(1, 6):
        response = await client.post("/auth/login", json={
            "user_name": f"nonexistent_{i}",
            "password": "qualquersenha",
        })
        assert response.status_code == 401, response.text

    response = await client.post("/auth/login", json={
        "user_name": "nonexistent_6",
        "password": "qualquersenha",
    })
    assert response.status_code == 429


async def test_login_requires_json_user_name_and_password(client):
    response = await client.post(
        "/auth/login",
        data={"username": "victor", "password": "senha123"},
    )

    assert response.status_code == 422


async def test_login_allows_configured_frontend_origin_with_credentials(client):
    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_registration_creates_one_portfolio_owned_by_user(client, async_db):
    credentials = {"user_name": "portfolio_owner", "password": "synthetic-password"}
    registered = await client.post("/auth/register", json=credentials)
    login = await client.post("/auth/login", json=credentials)
    portfolios = await client.get(
        "/portfolios", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )

    assert registered.status_code == 200
    assert portfolios.status_code == 200
    assert len(portfolios.json()) == 1
    portfolio_id = UUID(portfolios.json()[0]["id_portfolio"])
    persisted = await async_db.get(PortfolioModel, portfolio_id)
    assert str(persisted.user_id) == registered.json()["user_id"]


@pytest.mark.parametrize("path", ["/assets", "/portfolios"])
@pytest.mark.parametrize("token_kind", ["invalid", "unknown_user"])
async def test_protected_routes_reject_invalid_or_deleted_users(client, path, token_kind):
    token = "token.invalido.aqui"
    if token_kind == "unknown_user":
        token = get_token_handler().create_token(user_id=str(uuid4()))
    response = await client.get(path, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
