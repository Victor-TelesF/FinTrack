from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from ..database import Base
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .portfolio_model import PortfolioModel


class UserModel(Base):

    __tablename__ = "user"

    user_id: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid4)
    user_name: Mapped[str] = mapped_column(String(50))
    hash_password: Mapped[str] = mapped_column(String(250))
    portfolios: Mapped[list["PortfolioModel"]] = relationship(back_populates="user")
    

