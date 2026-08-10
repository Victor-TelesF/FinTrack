from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.mappers.asset_mapper import AssetMapper
from app.models import (
    AssetModel,
    CDBModel,
    CryptocurrencyModel,
    GovernmentBondModel,
    InternationalStockModel,
    NationalStockModel,
    RealEstateFundModel,
)
from app.schemas.asset_schema import AdminAssetItem, AssetBaseCreate
from app.schemas.fixed_income_schema import CDBCreate, GovernmentBondCreate
from app.schemas.variable_income_schema import (
    CryptocurrencyCreate,
    InternationalStockCreate,
    NationalStockCreate,
    RealEstateFundCreate,
)
from domain.assets.fixed_income.cdb import CDB
from domain.assets.fixed_income.government_bond import GovernmentBond
from domain.assets.variable_income.cryptocurrency import Cryptocurrency
from domain.assets.variable_income.international_stock import InternationalStock
from domain.assets.variable_income.national_stock import NationalStock
from domain.assets.variable_income.real_estate_fund import RealEstateFund
from app.errors.exceptions import AssetAlreadyExistsError, AssetNotFoundError


AssetCreate = TypeVar(
    "AssetCreate",
    CDBCreate,
    GovernmentBondCreate,
    NationalStockCreate,
    InternationalStockCreate,
    RealEstateFundCreate,
    CryptocurrencyCreate,
)


class AssetService:

    def __init__(self, db: Session):
        self._db = db

    def create(self, asset_data: AssetCreate) -> AssetModel:
        asset = _domain_asset_from_schema(asset_data)
        model = AssetMapper.to_model(asset)
        self._db.add(model)
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise AssetAlreadyExistsError()
        self._db.refresh(model)
        return model

    def list(self) -> list[AssetModel]:
        statement = select(AssetModel).order_by(AssetModel.ticker)
        return list(self._db.execute(statement).scalars().all())

    def get(self, asset_id: UUID) -> AssetModel:
        model = self._db.get(AssetModel, asset_id)
        if model is None:
            raise AssetNotFoundError()
        return model

    def upsert_many(self, assets: list[AdminAssetItem]) -> list[AssetModel]:
        models = []
        for asset_data in assets:
            domain_asset = _domain_asset_from_admin_item(asset_data)
            existing = self._db.execute(
                select(AssetModel).where(AssetModel.ticker == asset_data.ticker)
            ).scalar_one_or_none()
            if existing is None:
                model = AssetMapper.to_model(domain_asset)
                self._db.add(model)
            else:
                model = AssetMapper.to_model(domain_asset, model=existing)
            models.append(model)
        self._db.commit()
        for model in models:
            self._db.refresh(model)
        return models


def _domain_asset_from_schema(asset_data: AssetBaseCreate):
    common = {
        "name": asset_data.name,
        "ticker": asset_data.ticker,
        "current_price": asset_data.current_price,
    }
    if isinstance(asset_data, CDBCreate):
        return CDB(**common, rate=asset_data.rate, maturity_date=asset_data.maturity_date,
                   fgc_covered=asset_data.fgc_covered, liquidity_type=asset_data.liquidity_type,
                   index_type=asset_data.index_type)
    if isinstance(asset_data, GovernmentBondCreate):
        return GovernmentBond(**common, rate=asset_data.rate, maturity_date=asset_data.maturity_date,
                              liquidity_type=asset_data.liquidity_type,
                              bond_index_type=asset_data.bond_index_type)
    if isinstance(asset_data, NationalStockCreate):
        return NationalStock(**common)
    if isinstance(asset_data, InternationalStockCreate):
        return InternationalStock(**common)
    if isinstance(asset_data, RealEstateFundCreate):
        return RealEstateFund(**common)
    if isinstance(asset_data, CryptocurrencyCreate):
        return Cryptocurrency(**common)
    raise TypeError(f"Schema de ativo não suportado: {type(asset_data).__name__}")


def _domain_asset_from_admin_item(asset_data: AdminAssetItem):
    schema_types = {
        "cdb": CDBCreate,
        "government_bond": GovernmentBondCreate,
        "national_stock": NationalStockCreate,
        "international_stock": InternationalStockCreate,
        "real_estate_fund": RealEstateFundCreate,
        "cryptocurrency": CryptocurrencyCreate,
    }
    schema_type = schema_types[asset_data.type]
    return _domain_asset_from_schema(
        schema_type.model_validate(asset_data.model_dump())
    )