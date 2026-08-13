from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from uuid import uuid4, UUID
from ..models import UserModel, PortfolioModel
from ..auth import PasswordHandler, TokenHandler
from ..schemas.user_schema import UserCreate
from ..schemas.auth_schema import UserLogin, TokenRead
from ..errors.exceptions import InvalidCredentialsError, UserAlreadyExistsError
import asyncio


class AuthService:

    def __init__(self, db: AsyncSession, password_handler: PasswordHandler, token_handler: TokenHandler):
        self._db = db
        self._password_handler = password_handler
        self._token_handler = token_handler

    async def register(self, user_data: UserCreate) -> UserModel:

        stmt = select(UserModel).where(UserModel.user_name == user_data.user_name)
        if isinstance(self._db, AsyncSession):
            existing = await self._db.execute(stmt)
        else:
            existing = self._db.execute(stmt)
        existing_user = existing.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()

        hashed_password = await asyncio.to_thread(self._password_handler.hash_password, user_data.password)

        user = UserModel(
            user_name=user_data.user_name,
            hash_password=hashed_password,
            portfolios=[PortfolioModel(id_portfolio=uuid4())],
        )

        self._db.add(user)
        try:
            if isinstance(self._db, AsyncSession):
                await self._db.commit()
            else:
                self._db.commit()
        except IntegrityError:
            if isinstance(self._db, AsyncSession):
                await self._db.rollback()
            else:
                self._db.rollback()
            raise UserAlreadyExistsError()
        if isinstance(self._db, AsyncSession):
            await self._db.refresh(user)
        else:
            self._db.refresh(user)

        return user

    async def login(self, credentials: UserLogin) -> TokenRead:
        stmt = select(UserModel).where(UserModel.user_name == credentials.user_name)
        if isinstance(self._db, AsyncSession):
            result = await self._db.execute(stmt)
        else:
            result = self._db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise InvalidCredentialsError()

        is_valid = await asyncio.to_thread(self._password_handler.verify_password, credentials.password, user.hash_password)
        if not is_valid:
            raise InvalidCredentialsError()

        access_token = self._token_handler.create_token(user_id=str(user.user_id))

        return TokenRead(access_token=access_token, token_type="bearer")

    async def get_auth_user(self, token: str) -> UserModel:

        user = self._token_handler.decode_token(token)
        stmt = select(UserModel).where(UserModel.user_id == UUID(user))
        if isinstance(self._db, AsyncSession):
            result = await self._db.execute(stmt)
        else:
            result = self._db.execute(stmt)
        user_verification = result.scalar_one_or_none()

        if not user_verification:
            raise InvalidCredentialsError()

        return user_verification