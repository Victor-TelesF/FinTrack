import pytest
from pydantic import ValidationError

from app.config import Settings


def settings(**kwargs):
    return Settings(
        _env_file=None, POSTGRES_USER="test", POSTGRES_PASSWORD="test",
        POSTGRES_HOST="localhost", POSTGRES_PORT=5432, POSTGRES_DB="test",
        SECRET_KEY="synthetic", ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=30,
        **kwargs,
    )


def test_token_is_loaded_from_environment_and_redacted(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "synthetic-sensitive-token")
    config = settings()
    assert config.BRAPI_TOKEN.get_secret_value() == "synthetic-sensitive-token"
    assert "synthetic-sensitive-token" not in repr(config)
    assert "synthetic-sensitive-token" not in config.model_dump_json()


@pytest.mark.parametrize("field,value", [
    ("PRICE_FETCH_TIMEOUT_SECONDS", 0), ("PRICE_FETCH_TIMEOUT_SECONDS", "inf"),
    ("PRICE_CACHE_TTL_SECONDS", -1), ("PRICE_CACHE_TTL_SECONDS", "nan"),
    ("PRICE_CACHE_MAX_ENTRIES", 0), ("PRICE_HTTP_MAX_CONCURRENCY", 0),
    ("PRICE_HTTP_MAX_CONCURRENCY", 17), ("PRICE_BATCH_SIZE", 0), ("PRICE_BATCH_SIZE", 21),
])
def test_invalid_price_settings_fail_at_startup(field, value):
    with pytest.raises(ValidationError):
        settings(**{field: value})
