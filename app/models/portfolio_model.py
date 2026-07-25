from sqlalchemy import String, Numeric, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from typing import TYPE_CHECKING
from datetime import date
from ..database import Base
from uuid import UUID, uuid4
from domain.enums import TransactionType

if TYPE_CHECKING:
    from .user_model import UserModel


class TransactionModel(Base):

    __tablename__ = "transaction"

    id_transaction: Mapped[UUID] = mapped_column(primary_key=True, index=True,default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("asset.id", ondelete="RESTRICT"))
    id_portfolio: Mapped[UUID] = mapped_column(ForeignKey("portfolio.id_portfolio", ondelete="RESTRICT"))
    portfolio: Mapped["PortfolioModel"] = relationship(back_populates="transactions")
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=18,scale=8))
    price: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8))
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type_enum", create_constraint=True, validate_strings=True),nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date)


class PortfolioModel(Base):

    __tablename__ = "portfolio"

    id_portfolio: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid4)
    wallet_id: Mapped[str] = mapped_column(String(250))
    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="portfolio")
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.user_id", ondelete="RESTRICT"))
    user: Mapped["UserModel"] = relationship(back_populates="portfolios")
