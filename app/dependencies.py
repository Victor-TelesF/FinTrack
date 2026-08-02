from fastapi import Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .config import settings
from .auth import PasswordHandler, TokenHandler
from .service import AuthService


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_password_handler() -> PasswordHandler:
    return PasswordHandler()


def get_token_handler() -> TokenHandler:
    return TokenHandler(
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


def get_auth_service(
    db: Session = Depends(get_db),
    password_handler: PasswordHandler = Depends(get_password_handler),
    token_handler: TokenHandler = Depends(get_token_handler),
) -> AuthService:
    return AuthService(db, password_handler, token_handler)