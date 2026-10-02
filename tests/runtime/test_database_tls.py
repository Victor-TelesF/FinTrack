"""Opt-in real TLS checks against the disposable server started by the harness."""
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, pool, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.config import Settings
from pydantic import SecretStr


@pytest.fixture
def tls_settings():
    url = os.environ.get("FINTRACK_TLS_TEST_URL")
    if not url:
        pytest.skip("Run scripts/test_postgres_tls.py with disposable PostgreSQL binaries")
    config = Settings(
        _env_file=None, DATABASE_URL=url, SECRET_KEY="synthetic", ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
    )
    assert config.database_url.database == "fintrack_stage1_test"
    assert config.database_url.query["sslmode"] == "verify-full"
    return config


def test_sync_tls_and_release_with_special_password(tls_settings, monkeypatch):
    engine = create_engine(tls_settings.database_url, poolclass=pool.NullPool)
    schema = f"tls_migration_{uuid4().hex}"
    try:
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")) is True
            connection.execute(CreateSchema(schema))
        url = tls_settings.database_url.update_query_dict({"options": f"-csearch_path={schema}"})
        release_settings = tls_settings.model_copy(update={
            "DATABASE_URL": SecretStr(url.render_as_string(hide_password=False)),
        })
        monkeypatch.setattr("app.config.settings", release_settings)
        command.upgrade(Config("alembic.ini"), "head")
        with engine.connect() as connection:
            assert connection.scalar(text(f'SELECT version_num FROM "{schema}".alembic_version')) == "9d2a6c4e8f10"
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


@pytest.mark.asyncio
async def test_async_tls_and_real_readiness(tls_settings, monkeypatch):
    from app import main

    engine = create_async_engine(tls_settings.database_url, **tls_settings.database_pool_options)
    monkeypatch.setattr(main, "async_engine", engine)
    monkeypatch.setattr(main, "settings", tls_settings)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")) is True
        async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://testserver") as client:
            response = await client.get("/health/ready")
        assert response.status_code == 200 and response.json() == {"status": "ready"}
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["ca", "hostname"])
async def test_api_and_release_reject_invalid_tls(tls_settings, monkeypatch, invalid):
    from app import main

    url = tls_settings.database_url
    if invalid == "ca":
        url = url.update_query_dict({"sslrootcert": os.environ["FINTRACK_TLS_WRONG_CA"]})
        expected_error = "certificate verify failed"
    else:
        # Server certificate contains DNS:localhost only; no IP SAN.
        url = url.set(host="127.0.0.1")
        expected_error = "does not match host name"
    invalid_settings = tls_settings.model_copy(update={
        "DATABASE_URL": SecretStr(url.render_as_string(hide_password=False)),
    })
    monkeypatch.setattr("app.config.settings", invalid_settings)
    with pytest.raises(OperationalError, match=expected_error):
        command.upgrade(Config("alembic.ini"), "head")
    engine = create_async_engine(url, **invalid_settings.database_pool_options)
    monkeypatch.setattr(main, "async_engine", engine)
    monkeypatch.setattr(main, "settings", invalid_settings)
    try:
        async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://testserver") as client:
            live = await client.get("/health/live")
            ready = await client.get("/health/ready")
        assert live.status_code == 200
        assert ready.status_code == 503 and ready.json() == {"status": "unavailable"}
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


def test_tls_server_rejects_unencrypted_connection(tls_settings):
    engine = create_engine(tls_settings.database_url.update_query_dict({"sslmode": "disable"}))
    try:
        with pytest.raises(OperationalError, match="no encryption"):
            with engine.connect():
                pass
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_readiness_times_out_on_exhausted_pool_and_recovers(tls_settings, monkeypatch):
    from app import main

    config = tls_settings.model_copy(update={"DATABASE_POOL_SIZE": 1, "DATABASE_READY_TIMEOUT": 0.05})
    engine = create_async_engine(config.database_url, **config.database_pool_options)
    monkeypatch.setattr(main, "async_engine", engine)
    monkeypatch.setattr(main, "settings", config)
    try:
        async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://testserver") as client:
            async with engine.connect():
                response = await client.get("/health/ready")
                assert response.status_code == 503 and response.json() == {"status": "unavailable"}
                assert engine.pool.checkedout() == 1
            response = await client.get("/health/ready")
            assert response.status_code == 200 and response.json() == {"status": "ready"}
            assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()
