"""
Testes para AuthService.get_auth_user.

Cobre apenas o que é específico dessa camada (validação de token já é
coberta em test_token_handler.py):
- Token válido + usuário existe no banco → retorna o UserModel correto
- Token válido, mas usuário não existe mais no banco → InvalidCredentialsError
- Token inválido/adulterado → propaga InvalidTokenError vindo do TokenHandler
"""
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.database import Base
from app.service.auth_service import AuthService
from app.auth import PasswordHandler, TokenHandler
from app.schemas.user_schema import UserCreate
from app.errors.exceptions import InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError

settings_teste = Settings(_env_file=".env.test")
engine_teste = create_engine(settings_teste.database_url)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)


@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture
def db(setup_database):
    session = SessionTeste()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def token_handler():
    return TokenHandler(
        secret_key=settings_teste.SECRET_KEY,
        algorithm=settings_teste.ALGORITHM,
        expire_minutes=settings_teste.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@pytest.fixture
def auth_service(db, token_handler):
    return AuthService(db, PasswordHandler(), token_handler)


@pytest.fixture
async def registered_user(auth_service):
    return await auth_service.register(UserCreate(user_name="victor", password="senha123"))


class TestGetAuthUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_correct_user(self, auth_service, registered_user, token_handler):
        token = token_handler.create_token(user_id=str(registered_user.user_id))
        result = await auth_service.get_auth_user(token)
        assert result.user_id == registered_user.user_id
        assert result.user_name == registered_user.user_name

    @pytest.mark.asyncio
    async def test_valid_token_but_user_not_in_db_raises(self, auth_service, token_handler):
        token = token_handler.create_token(user_id=str(uuid4()))
        with pytest.raises(InvalidCredentialsError):
            await auth_service.get_auth_user(token)

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self, auth_service):
        with pytest.raises(InvalidTokenError):
            await auth_service.get_auth_user("token.invalido.aqui")


class TestRegisterHandlesIntegrityError:
    def test_commit_integrity_error_is_converted_to_user_already_exists(
        self, auth_service, db, monkeypatch
    ):
        def fake_commit():
            raise IntegrityError("INSERT INTO user...", params={}, orig=Exception("duplicate key"))

        monkeypatch.setattr(db, "commit", fake_commit)

        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(UserCreate(user_name="victor", password="senha123"))