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


def get_portfolio_service(db: AsyncSession = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)
async def get_current_user(user_credential: AuthService = Depends(get_auth_service),
                           token: str = Depends(oauth2_scheme)) -> UserModel:
    # TODO fase 2: AuthService.get_auth_user becomes async and this must `await`
    return user_credential.get_auth_user(token)