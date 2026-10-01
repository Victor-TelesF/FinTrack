from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ADMIN_KEY: str = ""
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
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
         f"{self.POSTGRES_PORT}/"
         f"{self.POSTGRES_DB}"
         )

settings = Settings()
