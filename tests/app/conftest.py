import json
from pathlib import Path

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app import dependencies, main
from app.config import Settings
from app.database import AsyncSessionLocal, Base
from app.routers.auth_router import reset_rate_limit_state


@pytest.fixture
def test_settings():
    return Settings(_env_file=".env.test")


@pytest.fixture
def sync_engine(test_settings):
    engine = create_engine(test_settings.database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def setup_database(sync_engine):
    Base.metadata.create_all(bind=sync_engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=sync_engine)


@pytest_asyncio.fixture
async def async_engine(setup_database, test_settings):
    engine = create_async_engine(test_settings.database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def async_session_factory(async_engine, monkeypatch):
    def make_session():
        # Exercise production session options against the isolated test engine.
        return AsyncSessionLocal(bind=async_engine)

    monkeypatch.setattr(dependencies, "AsyncSessionLocal", make_session)
    return make_session


@pytest_asyncio.fixture
async def async_db(async_session_factory):
    async with async_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def isolate_app_state():
    previous_overrides = main.app.dependency_overrides.copy()
    reset_rate_limit_state()
    try:
        yield
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous_overrides)
        reset_rate_limit_state()


@pytest.fixture
def test_app(async_engine, async_session_factory, monkeypatch):
    monkeypatch.setattr(main, "async_engine", async_engine)
    return main.app


@pytest_asyncio.fixture
async def client(test_app):
    async with LifespanManager(test_app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app), base_url="http://testserver"
        ) as client:
            yield client


@pytest.fixture
def legacy_http_examples():
    path = Path(__file__).resolve().parents[1] / "contracts" / "legacy-http-examples.json"
    return {example["name"]: example for example in json.loads(path.read_text())["examples"]}
