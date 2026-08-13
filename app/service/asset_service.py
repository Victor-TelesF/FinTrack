from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from sqlalchemy.orm import selectin_polymorphic
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

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, asset_data: AssetCreate) -> AssetModel:
        asset = _domain_asset_from_schema(asset_data)
        model = AssetMapper.to_model(asset)
        self._db.add(model)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise AssetAlreadyExistsError()
        await self._db.refresh(model)
        return _model_payload(model)

    async def list(self) -> list[AssetModel]:
        statement = (
            select(AssetModel)
            .options(
                selectin_polymorphic(AssetModel, [
                    CDBModel,
                    GovernmentBondModel,
                    NationalStockModel,
                    InternationalStockModel,
                    RealEstateFundModel,
                    CryptocurrencyModel,
                ])
            )
            .order_by(AssetModel.ticker)
        )
        result = await self._db.execute(statement)
        models = list(result.scalars().all())
        return [_model_payload(m) for m in models]

    async def get(self, asset_id: UUID) -> AssetModel:
        statement = (
            select(AssetModel)
            .where(AssetModel.id == asset_id)
            .options(
                selectin_polymorphic(AssetModel, [
                    CDBModel,
                    GovernmentBondModel,
                    NationalStockModel,
                    InternationalStockModel,
                    RealEstateFundModel,
                    CryptocurrencyModel,
                ])
            )
        )
        result = await self._db.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise AssetNotFoundError()
        return _model_payload(model)

    async def upsert_many(self, assets: list[AdminAssetItem]) -> list[AssetModel]:
        models = []
        for asset_data in assets:
            domain_asset = _domain_asset_from_admin_item(asset_data)
            result = await self._db.execute(
                select(AssetModel).where(AssetModel.ticker == asset_data.ticker)
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                model = AssetMapper.to_model(domain_asset)
                self._db.add(model)
            else:
                model = AssetMapper.to_model(domain_asset, model=existing)
            # populate infrastructure-only field external_price_id
            # For cryptocurrencies, external_price_id must be explicitly provided (validated by schema)
            model.external_price_id = (
                asset_data.external_price_id
                if asset_data.external_price_id
                else (None if asset_data.type == "cryptocurrency" else asset_data.ticker)
            )
            models.append(model)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise AssetAlreadyExistsError()
        for model in models:
            await self._db.refresh(model)
        return [_model_payload(m) for m in models]


def _model_payload(model: AssetModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "ticker": model.ticker,
        "current_price": model.current_price,
        "asset_type": model.asset_type,
        "rate": getattr(model, "rate", None),
        "maturity_date": getattr(model, "maturity_date", None),
        "fgc_covered": getattr(model, "fgc_covered", None),
        "liquidity_type": getattr(model, "liquidity_type", None),
        "index_type": getattr(model, "index_type", None),
        "bond_index_type": getattr(model, "bond_index_type", None),
    }


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