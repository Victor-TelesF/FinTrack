import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base
from app.main import app
from app.dependencies import get_db

settings_teste = Settings(_env_file=".env.test")
engine_teste = create_engine(settings_teste.database_url)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)


def get_db_teste():
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = get_db_teste


@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture
def client(setup_database):
    return TestClient(app)