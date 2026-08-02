"""
Testes para TokenHandler.

Cobre:
- create_token gera um token (string) não vazio
- decode_token de um token recém-criado devolve o mesmo user_id usado na criação
- decode_token de um token adulterado levanta InvalidTokenError
- decode_token de um token expirado levanta InvalidTokenError
- decode_token de um token assinado com uma secret_key diferente levanta InvalidTokenError
"""
import time

import pytest

from app.auth.token_handler import TokenHandler
from app.exceptions import InvalidTokenError


@pytest.fixture
def handler():
    return TokenHandler(secret_key="chave-secreta-de-teste", algorithm="HS256", expire_minutes=30)


class TestCreateToken:
    def test_create_token_returns_a_non_empty_string(self, handler):
        token = handler.create_token(user_id="user-123")
        assert isinstance(token, str)
        assert len(token) > 0


class TestDecodeToken:
    def test_decode_returns_the_same_user_id_used_to_create_the_token(self, handler):
        token = handler.create_token(user_id="user-123")
        assert handler.decode_token(token) == "user-123"

    def test_decode_tampered_token_raises(self, handler):
        token = handler.create_token(user_id="user-123")
        tampered_token = token[:-5] + "XXXXX"
        with pytest.raises(InvalidTokenError):
            handler.decode_token(tampered_token)

    def test_decode_expired_token_raises(self):
        handler_curto = TokenHandler(secret_key="chave-secreta-de-teste", algorithm="HS256", expire_minutes=0)
        token = handler_curto.create_token(user_id="user-456")
        time.sleep(1)
        with pytest.raises(InvalidTokenError):
            handler_curto.decode_token(token)

    def test_decode_token_signed_with_different_secret_key_raises(self, handler):
        token = handler.create_token(user_id="user-123")
        outro_handler = TokenHandler(secret_key="outra-chave-diferente", algorithm="HS256", expire_minutes=30)
        with pytest.raises(InvalidTokenError):
            outro_handler.decode_token(token)