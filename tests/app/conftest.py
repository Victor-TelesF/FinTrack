import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import Settings
from app.database import Base
from app.main import app
from app.dependencies import get_db
from app.routers.auth_router import reset_rate_limit_state

settings_teste = Settings(_env_file=".env.test")
engine_teste = create_engine(settings_teste.database_url)
async_engine_teste = create_async_engine(settings_teste.database_url)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)
AsyncSessionTeste = async_sessionmaker(async_engine_teste, expire_on_commit=False, autoflush=False)


async def get_db_teste():
    async with AsyncSessionTeste() as db:
        yield db


app.dependency_overrides[get_db] = get_db_teste


@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture
def client(setup_database):
    reset_rate_limit_state()
    with TestClient(app) as tc:
        yield tc