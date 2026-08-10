def test_register_creates_user(client):
    response = client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    assert response.status_code == 200
    assert response.json()["user_name"] == "victor"


def test_register_duplicate_user_name_raises_conflict(client):
    client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = client.post("/auth/register", json={
        "user_name": "victor",
        "password": "outrasenha456",
    })

    assert response.status_code == 409


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = client.post("/auth/login", json={
        "user_name": "victor",
        "password": "senha123",
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_with_nonexistent_user_raises_invalid_credentials(client):
    response = client.post("/auth/login", json={
        "user_name": "nao_existe",
        "password": "qualquersenha",
    })

    assert response.status_code == 401


def test_login_with_wrong_password_raises_invalid_credentials(client):
    client.post("/auth/register", json={
        "user_name": "victor",
        "password": "senha123",
    })

    response = client.post("/auth/login", json={
        "user_name": "victor",
        "password": "senhaerrada",
    })

    assert response.status_code == 401


def test_login_requires_json_user_name_and_password(client):
    response = client.post(
        "/auth/login",
        data={"username": "victor", "password": "senha123"},
    )

    assert response.status_code == 422


def test_login_allows_configured_frontend_origin_with_credentials(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"