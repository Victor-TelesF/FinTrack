from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import uuid4, UUID
from ..models import UserModel, PortfolioModel
from ..auth import PasswordHandler, TokenHandler
from ..schemas.user_schema import UserCreate
from ..schemas.auth_schema import UserLogin, TokenRead
from ..errors.exceptions import InvalidCredentialsError, UserAlreadyExistsError

class AuthService:

    def __init__(self, db: Session, password_handler: PasswordHandler, token_handler: TokenHandler):
        self._db = db
        self._password_handler = password_handler
        self._token_handler = token_handler

    def register(self, user_data: UserCreate) -> UserModel:

        stmt = select(UserModel).where(UserModel.user_name == user_data.user_name)
        existing_user = self._db.execute(stmt).scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()


        hashed_password = self._password_handler.hash_password(user_data.password)

        user = UserModel(
            user_name=user_data.user_name,
            hash_password=hashed_password,
            portfolios=[PortfolioModel(id_portfolio=uuid4())],
        )

        self._db.add(user)
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise UserAlreadyExistsError()
        self._db.refresh(user)

        return user

    def login(self, credentials: UserLogin) -> TokenRead:
        stmt = select(UserModel).where(UserModel.user_name == credentials.user_name)
        user = self._db.execute(stmt).scalar_one_or_none()

        if user is None:
            raise InvalidCredentialsError()

        if not self._password_handler.verify_password(credentials.password, user.hash_password):
            raise InvalidCredentialsError()

        access_token = self._token_handler.create_token(user_id=str(user.user_id))

        return TokenRead(access_token=access_token, token_type="bearer")

    def get_auth_user(self, token: str) -> UserModel:

        user = self._token_handler.decode_token(token)
        stmt = select(UserModel).where(UserModel.user_id == UUID(user))
        user_verification = self._db.execute(stmt).scalar_one_or_none()

        if not user_verification:
            raise InvalidCredentialsError()

        return user_verification