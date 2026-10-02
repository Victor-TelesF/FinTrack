"""Database configuration checks need no running PostgreSQL or application fixtures."""
import io
import runpy
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import URL, pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings


@pytest.fixture
def make_settings(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)

    def build(**overrides):
        values = dict(
            _env_file=None, POSTGRES_USER="synthetic", POSTGRES_PASSWORD="synthetic",
            POSTGRES_HOST="localhost", POSTGRES_DB="synthetic", DATABASE_SSLMODE="disable",
            SECRET_KEY="synthetic", ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=30,
        )
        values.update(overrides)
        return Settings(**values)

    return build


def test_special_component_password_and_redaction(make_settings):
    password = "synthetic@:/%?# +secret"
    config = make_settings(POSTGRES_PASSWORD=password)
    assert isinstance(config.database_url, URL)
    assert config.database_url.password == password
    assert config.database_url.host == "localhost"
    assert config.database_url.query == {"sslmode": "disable", "connect_timeout": "5"}
    for diagnostic in (repr(config), config.model_dump_json(), config.redacted_database_url):
        assert password not in diagnostic
    assert "***" in config.redacted_database_url


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_external_url_precedence_and_preservation(make_settings, scheme):
    url = (f"{scheme}://external:synthetic%40%25%2F@db.example:6543/external"
           "?sslmode=verify-full&sslrootcert=%2Fruntime%2Fca.pem"
           "&application_name=fintrack&connect_timeout=7&options=-cstatement_timeout%3D5000")
    config = make_settings(DATABASE_URL=url, DATABASE_SSLROOTCERT="/ignored.pem")
    actual = config.database_url
    assert (actual.drivername, actual.username, actual.password, actual.host, actual.port, actual.database) == (
        "postgresql+psycopg", "external", "synthetic@%/", "db.example", 6543, "external",
    )
    assert actual.query == {
        "sslmode": "verify-full", "sslrootcert": "/runtime/ca.pem", "application_name": "fintrack",
        "connect_timeout": "7", "options": "-cstatement_timeout=5000",
    }
    assert "synthetic%40" not in config.model_dump_json()
    assert "options" not in config.redacted_database_url


def test_url_only_configuration_and_tls_defaults(make_settings):
    config = make_settings(
        DATABASE_URL="postgresql://external:synthetic@db.example/test",
        POSTGRES_USER=None, POSTGRES_PASSWORD=None, POSTGRES_HOST=None, POSTGRES_DB=None,
        DATABASE_SSLMODE="verify-full", DATABASE_SSLROOTCERT="/runtime/ca.pem",
    )
    assert config.database_url.query["sslmode"] == "verify-full"
    assert config.database_url.query["sslrootcert"] == "/runtime/ca.pem"


def test_empty_url_uses_components(make_settings):
    assert make_settings(DATABASE_URL="").database_url.database == "synthetic"


@pytest.mark.parametrize("overrides", [
    {"POSTGRES_HOST": None},
    {"DATABASE_SSLMODE": "verify-full"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host/db?sslmode=require"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host/db?sslmode=verify-full"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host/db?sslmode=disable&connect_timeout=0"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host/db?sslmode=disable&connect_timeout=bad"},
    {"DATABASE_URL": "synthetic-url-secret"},
    {"DATABASE_URL": "sqlite:///synthetic-url-secret"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host:bad/db"},
    {"DATABASE_URL": "postgresql://user:synthetic-url-secret@host:70000/db"},
    {"DATABASE_URL": "postgresql:///db?sslmode=verify-full&sslrootcert=/ca.pem"},
    {"DATABASE_URL": "postgresql://host/db?host=/tmp&sslmode=verify-full&sslrootcert=/ca.pem"},
    {"DATABASE_POOL_SIZE": 0}, {"DATABASE_MAX_OVERFLOW": -1},
    {"DATABASE_POOL_TIMEOUT": "inf"}, {"DATABASE_READY_TIMEOUT": "nan"},
    {"DATABASE_CONNECT_TIMEOUT": 0},
])
def test_invalid_configuration_has_safe_startup_error(make_settings, overrides):
    with pytest.raises(ValidationError) as exc:
        make_settings(**overrides)
    assert "synthetic-url-secret" not in str(exc.value)
    assert "input_value" not in str(exc.value)


@pytest.mark.asyncio
async def test_pool_defaults_and_custom_options(make_settings):
    for config, size, overflow, timeout in (
        (make_settings(), 3, 0, 10),
        (make_settings(DATABASE_POOL_SIZE=2, DATABASE_MAX_OVERFLOW=1, DATABASE_POOL_TIMEOUT=4), 2, 1, 4),
    ):
        engine = create_async_engine(config.database_url, **config.database_pool_options)
        try:
            assert engine.pool.size() == size
            assert engine.pool._max_overflow == overflow
            assert engine.pool._timeout == timeout
            assert engine.pool._pre_ping is True
            assert engine.sync_engine.hide_parameters is True
        finally:
            await engine.dispose()


def test_alembic_offline_accepts_percent_password(make_settings, monkeypatch):
    monkeypatch.setattr("app.config.settings", make_settings(POSTGRES_PASSWORD="synthetic@%/secret"))
    output = io.StringIO()
    command.upgrade(Config("alembic.ini", output_buffer=output), "head", sql=True)
    assert "CREATE TABLE" in output.getvalue()
    assert "synthetic@" not in output.getvalue()


def test_alembic_online_receives_same_tls_url_and_nullpool(make_settings, monkeypatch):
    config = make_settings(DATABASE_SSLMODE="verify-full", DATABASE_SSLROOTCERT="/runtime/ca.pem")
    monkeypatch.setattr("app.config.settings", config)
    factory = MagicMock()
    monkeypatch.setattr("sqlalchemy.create_engine", factory)
    monkeypatch.setattr("alembic.context.config", Config("alembic.ini"), raising=False)
    monkeypatch.setattr("alembic.context.is_offline_mode", lambda: False)
    monkeypatch.setattr("alembic.context.configure", MagicMock())
    monkeypatch.setattr("alembic.context.begin_transaction", MagicMock())
    monkeypatch.setattr("alembic.context.run_migrations", MagicMock())
    runpy.run_path("alembic/env.py")
    factory.assert_called_once_with(config.database_url, poolclass=pool.NullPool, hide_parameters=True)
    factory.return_value.dispose.assert_called_once()
