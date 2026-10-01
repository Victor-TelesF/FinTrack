"""
Testes para AuthService.get_auth_user.

Cobre apenas o que é específico dessa camada (validação de token já é
coberta em test_token_handler.py):
- Token válido + usuário existe no banco → retorna o UserModel correto
- Token válido, mas usuário não existe mais no banco → InvalidCredentialsError
- Token inválido/adulterado → propaga InvalidTokenError vindo do TokenHandler
"""
from uuid import uuid4
from threading import get_ident
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.service.auth_service import AuthService
from app.auth import PasswordHandler, TokenHandler
from app.schemas.user_schema import UserCreate
from app.schemas.auth_schema import UserLogin
from app.models import PortfolioModel, UserModel
from app.errors.exceptions import InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError

pytestmark = pytest.mark.asyncio


@pytest.fixture
def token_handler(test_settings):
    return TokenHandler(
        secret_key=test_settings.SECRET_KEY,
        algorithm=test_settings.ALGORITHM,
        expire_minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@pytest.fixture
def auth_service(async_db, token_handler):
    return AuthService(async_db, PasswordHandler(), token_handler)


@pytest_asyncio.fixture
async def registered_user(auth_service):
    return await auth_service.register(UserCreate(user_name="victor", password="senha123"))


class TestGetAuthUser:
    async def test_valid_token_returns_correct_user(self, auth_service, registered_user, token_handler):
        token = token_handler.create_token(user_id=str(registered_user.user_id))
        result = await auth_service.get_auth_user(token)
        assert result.user_id == registered_user.user_id
        assert result.user_name == registered_user.user_name

    async def test_valid_token_but_user_not_in_db_raises(self, auth_service, token_handler):
        token = token_handler.create_token(user_id=str(uuid4()))
        with pytest.raises(InvalidCredentialsError):
            await auth_service.get_auth_user(token)

    async def test_invalid_token_raises(self, auth_service):
        with pytest.raises(InvalidTokenError):
            await auth_service.get_auth_user("token.invalido.aqui")


class TestRegisterHandlesIntegrityError:
    async def test_commit_integrity_error_is_converted_to_user_already_exists(
        self, auth_service, async_db, monkeypatch
    ):
        async def fail_after_flush():
            await async_db.flush()
            raise IntegrityError("INSERT INTO user...", params={}, orig=Exception("duplicate key"))

        commit = AsyncMock(side_effect=fail_after_flush)
        monkeypatch.setattr(async_db, "commit", commit)

        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(UserCreate(user_name="victor", password="senha123"))

        commit.assert_awaited_once()
        assert await async_db.scalar(select(func.count()).select_from(UserModel)) == 0
        assert await async_db.scalar(select(func.count()).select_from(PortfolioModel)) == 0


async def test_password_operations_run_outside_event_loop(auth_service, monkeypatch):
    loop_thread = get_ident()
    threads = {}

    def hash_password(self, password):
        threads["hash"] = get_ident()
        return "synthetic-hash"

    def verify_password(self, password, hashed_password):
        threads["verify"] = get_ident()
        return password == "synthetic-password" and hashed_password == "synthetic-hash"

    monkeypatch.setattr(PasswordHandler, "hash_password", hash_password)
    monkeypatch.setattr(PasswordHandler, "verify_password", verify_password)

    await auth_service.register(UserCreate(user_name="thread_user", password="synthetic-password"))
    token = await auth_service.login(UserLogin(user_name="thread_user", password="synthetic-password"))

    assert token.token_type == "bearer"
    assert set(threads) == {"hash", "verify"}
    assert all(thread != loop_thread for thread in threads.values())
