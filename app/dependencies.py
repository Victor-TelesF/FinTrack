from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal
from .config import settings
from .auth import PasswordHandler, TokenHandler
from .service import AuthService
from .service.asset_service import AssetService
from .service.portfolio_service import PortfolioService
from .models import UserModel
from fastapi import Request
import httpx
from app.price_sources.cache import SimplePriceCache
from app.price_sources.brapi_source import BrapiSource
from app.price_sources.twelvedata_source import TwelveDataSource
from app.price_sources.coingecko_source import CoinGeckoSource
from app.price_sources.market_price_source import MarketPriceSource
from app.price_source import DatabasePriceSource
from domain.protocols import PriceSource

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

def get_password_handler() -> PasswordHandler:
    return PasswordHandler()

def get_token_handler() -> TokenHandler:
    return TokenHandler(
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

def get_auth_service(
    db: AsyncSession = Depends(get_db),
    password_handler: PasswordHandler = Depends(get_password_handler),
    token_handler: TokenHandler = Depends(get_token_handler),
) -> AuthService:
    return AuthService(db, password_handler, token_handler)


def get_asset_service(db: AsyncSession = Depends(get_db)) -> AssetService:
    return AssetService(db)

async def get_current_user(user_credential: AuthService = Depends(get_auth_service),
                           token: str = Depends(oauth2_scheme)) -> UserModel:
    return await user_credential.get_auth_user(token)


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_price_cache(request: Request) -> SimplePriceCache:
    return request.app.state.price_cache


def get_price_source(
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
    cache: SimplePriceCache = Depends(get_price_cache),
) -> PriceSource:
    adapters = {
        "national_stock": BrapiSource(client, settings.BRAPI_TOKEN),
        "real_estate_fund": BrapiSource(client, settings.BRAPI_TOKEN),
        "international_stock": TwelveDataSource(client, settings.TWELVEDATA_API_KEY),
        "cryptocurrency": CoinGeckoSource(client),
    }
    fallback = DatabasePriceSource(db)
    return MarketPriceSource(adapters, fallback, cache)


def get_portfolio_service(db: AsyncSession = Depends(get_db), price_source: PriceSource = Depends(get_price_source)) -> PortfolioService:
    return PortfolioService(db, price_source)