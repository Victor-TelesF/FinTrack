"""
Testes para PasswordHandler.

Cobre:
- hash_password gera um hash diferente da senha original
- hash_password usa salt aleatório (duas chamadas com a mesma senha geram hashes diferentes)
- verify_password retorna True para a senha correta
- verify_password retorna False para a senha incorreta
- verify_password funciona mesmo com hashes diferentes da mesma senha (efeito do salt)
"""
import pytest

from app.auth.password_handler import PasswordHandler


@pytest.fixture
def handler():
    return PasswordHandler()


class TestHashPassword:
    def test_hash_is_different_from_original_password(self, handler):
        senha = "minhasenha123"
        hash_gerado = handler.hash_password(senha)
        assert hash_gerado != senha

    def test_hashing_same_password_twice_produces_different_hashes(self, handler):
        """Regressão do comportamento de salt aleatório: mesma senha, hashes diferentes."""
        senha = "minhasenha123"
        hash_1 = handler.hash_password(senha)
        hash_2 = handler.hash_password(senha)
        assert hash_1 != hash_2


class TestVerifyPassword:
    def test_verify_returns_true_for_correct_password(self, handler):
        senha = "minhasenha123"
        hash_gerado = handler.hash_password(senha)
        assert handler.verify_password(senha, hash_gerado) is True

    def test_verify_returns_false_for_incorrect_password(self, handler):
        senha = "minhasenha123"
        hash_gerado = handler.hash_password(senha)
        assert handler.verify_password("senhaerrada", hash_gerado) is False

    def test_verify_works_across_different_hashes_of_same_password(self, handler):
        """Mesmo com hashes diferentes (salt diferente), ambos devem validar a senha original."""
        senha = "minhasenha123"
        hash_1 = handler.hash_password(senha)
        hash_2 = handler.hash_password(senha)

        assert handler.verify_password(senha, hash_1) is True
        assert handler.verify_password(senha, hash_2) is True