from sqlalchemy import String, Integer, ForeignKey, Date, Numeric, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from decimal import Decimal
from ..database import Base
import uuid
from domain.enums import IndexType, BondIndexType, LiquidityType
from enum import Enum

class AssetModel(Base):

    __tablename__ = "asset"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, index=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    ticker: Mapped[str] = mapped_column(String(50))
    current_price: Mapped[Decimal] = mapped_column(Numeric(precision=18,scale=8))
    type_column: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {
        "polymorphic_on": type_column,
        "polymorphic_identity": "asset"
    }

class FixedIncomeModel(AssetModel):

    __tablename__ = "fixed_income"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("asset.id"), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric)
    maturity_date: Mapped[date] = mapped_column(Date)

    __mapper_args__ = {"polymorphic_identity": "fixed_income"}

class CDBModel(FixedIncomeModel):

    __tablename__ = "cdb"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fixed_income.id"), primary_key=True)
    fgc_covered: Mapped[bool] = mapped_column(Boolean)
    liquidity_type: Mapped[LiquidityType] = mapped_column(Enum(LiquidityType, name="liquidity_type_enum", create_constraint=True, validate_strings=True), nullable=False)
    index_type: Mapped[IndexType] = mapped_column(Enum(IndexType, name="index_type_enum", create_constraint=True, validate_strings=True), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "cdb"}