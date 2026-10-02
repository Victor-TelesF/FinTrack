from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    DATABASE_URL: SecretStr | None = Field(default=None, repr=False)
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: SecretStr | None = Field(default=None, repr=False)
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str | None = None
    DATABASE_SSLMODE: Literal["disable", "verify-full"] = "verify-full"
    DATABASE_SSLROOTCERT: str | None = None
    DATABASE_CONNECT_TIMEOUT: int = Field(default=5, gt=0)
    DATABASE_POOL_SIZE: int = Field(default=3, gt=0)
    DATABASE_MAX_OVERFLOW: int = Field(default=0, ge=0)
    DATABASE_POOL_TIMEOUT: float = Field(default=10, gt=0, allow_inf_nan=False)
    DATABASE_READY_TIMEOUT: float = Field(default=3, gt=0, allow_inf_nan=False)

    SECRET_KEY: str = Field(repr=False, exclude=True)
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ADMIN_KEY: str = Field(default="", repr=False, exclude=True)
    FRONTEND_ORIGINS: str = "http://localhost:3000"
    BRAPI_TOKEN: SecretStr = Field(default=SecretStr(""), repr=False)
    PRICE_FETCH_TIMEOUT_SECONDS: float = Field(default=10, gt=0, allow_inf_nan=False)
    PRICE_CACHE_TTL_SECONDS: float = Field(default=1800, gt=0, allow_inf_nan=False)
    PRICE_CACHE_MAX_ENTRIES: int = Field(default=1000, gt=0)
    PRICE_HTTP_MAX_CONCURRENCY: int = Field(default=1, ge=1, le=16)
    PRICE_BATCH_SIZE: int = Field(default=1, ge=1, le=20)

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url(self) -> URL:
        if self.DATABASE_URL and self.DATABASE_URL.get_secret_value().strip():
            try:
                url = make_url(self.DATABASE_URL.get_secret_value())
                # Access port here as malformed ports can fail lazily.
                url.port
            except (ArgumentError, ValueError, TypeError):
                raise ValueError("Invalid PostgreSQL URL") from None
            if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
                raise ValueError("Database URL must use PostgreSQL with psycopg")
            if url.port is not None and not 1 <= url.port <= 65535:
                raise ValueError("Invalid PostgreSQL port")
            url = url.set(drivername="postgresql+psycopg")
        else:
            if not all((self.POSTGRES_USER, self.POSTGRES_PASSWORD,
                        self.POSTGRES_HOST, self.POSTGRES_DB)):
                raise ValueError("Configure DATABASE_URL or all PostgreSQL components")
            url = URL.create(
                "postgresql+psycopg", username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD.get_secret_value(),
                host=self.POSTGRES_HOST, port=self.POSTGRES_PORT, database=self.POSTGRES_DB,
            )
        # URL query options take precedence; do not discard provider options.
        query = dict(url.query)
        query.setdefault("sslmode", self.DATABASE_SSLMODE)
        if self.DATABASE_SSLROOTCERT:
            query.setdefault("sslrootcert", self.DATABASE_SSLROOTCERT)
        query.setdefault("connect_timeout", str(self.DATABASE_CONNECT_TIMEOUT))
        if query["sslmode"] not in {"disable", "verify-full"}:
            raise ValueError("Database TLS must use verify-full or explicit disable")
        if query["sslmode"] == "verify-full" and not query.get("sslrootcert"):
            raise ValueError("verify-full requires an explicit database CA file")
        if "sslrootcert" in query and not isinstance(query["sslrootcert"], str):
            raise ValueError("Configure only one database CA file")
        if query["sslmode"] == "verify-full":
            hosts = query.get("host", url.host)
            if not hosts or any(host.startswith("/") for host in (
                hosts if isinstance(hosts, tuple) else hosts.split(",")
            )):
                raise ValueError("verify-full requires a TCP database hostname")
        try:
            if int(query["connect_timeout"]) <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Database connect timeout must be a positive integer") from None
        return url.set(query=query)

    @property
    def redacted_database_url(self) -> str:
        # Query options may themselves contain credentials; omit them from diagnostics.
        return self.database_url.set(query={}).render_as_string(hide_password=True)

    @property
    def database_pool_options(self) -> dict:
        return {
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": self.DATABASE_POOL_TIMEOUT,
            "pool_pre_ping": True,
            "hide_parameters": True,
        }

    @model_validator(mode="after")
    def validate_database_configuration(self):
        self.database_url
        return self


settings = Settings()
