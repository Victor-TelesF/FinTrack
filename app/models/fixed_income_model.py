from sqlalchemy import ForeignKey, Date, Numeric, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from decimal import Decimal
from uuid import UUID
from domain.enums import IndexType, BondIndexType, LiquidityType
from .asset_model import AssetModel


class FixedIncomeModel(AssetModel):

    __tablename__ = "fixed_income"

    id: Mapped[UUID] = mapped_column(ForeignKey("asset.id"), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8))
    maturity_date: Mapped[date] = mapped_column(Date)

    __mapper_args__ = {"polymorphic_identity": "fixed_income"}

class CDBModel(FixedIncomeModel):

    __tablename__ = "cdb"

    id: Mapped[UUID] = mapped_column(ForeignKey("fixed_income.id"), primary_key=True)
    fgc_covered: Mapped[bool] = mapped_column(Boolean)
    liquidity_type: Mapped[LiquidityType] = mapped_column(Enum(LiquidityType, name="liquidity_type_enum", create_constraint=True, validate_strings=True), nullable=False)
    index_type: Mapped[IndexType] = mapped_column(Enum(IndexType, name="index_type_enum", create_constraint=True, validate_strings=True), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "cdb"}

class GovernmentBondModel(FixedIncomeModel):
    __tablename__ = "government_bond"

    id: Mapped[UUID] = mapped_column(ForeignKey("fixed_income.id"), primary_key=True)
    liquidity_type: Mapped[LiquidityType] = mapped_column(Enum(LiquidityType,name="liquidity_type_enum", create_constraint=True, validate_strings=True), nullable=False)
    bond_index_type: Mapped[BondIndexType] = mapped_column(Enum(BondIndexType,name="bond_index_type_enum", create_constraint=True, validate_strings=True), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "government_bond"}