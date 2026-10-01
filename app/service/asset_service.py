from __future__ import annotations

import re
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_polymorphic

from app.mappers.asset_mapper import AssetMapper
from app.models import (
    AssetModel,
    TransactionModel,
    CDBModel,
    CryptocurrencyModel,
    GovernmentBondModel,
    InternationalStockModel,
    NationalStockModel,
    RealEstateFundModel,
)
from app.schemas.asset_schema import AdminAssetItem, AssetBaseCreate, QuoteMetadata
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
from app.errors.exceptions import (
    AssetAlreadyExistsError, AssetNotFoundError, AssetCurrencyLockedError,
    InvalidAssetQuoteMetadataError,
)


AssetCreate = TypeVar(
    "AssetCreate",
    CDBCreate,
    GovernmentBondCreate,
    NationalStockCreate,
    InternationalStockCreate,
    RealEstateFundCreate,
    CryptocurrencyCreate,
)

# Include joined-inheritance columns before mapping or response serialization.
catalog_asset = with_polymorphic(AssetModel, "*")


class AssetService:

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, asset_data: AssetCreate) -> AssetModel:
        asset = _domain_asset_from_schema(asset_data)
        model = AssetMapper.to_model(asset)
        _apply_quote_metadata(model, asset_data, new=True)
        self._db.add(model)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise AssetAlreadyExistsError()
        await self._db.refresh(model)
        return model

    async def list(self) -> list[AssetModel]:
        statement = select(catalog_asset).order_by(catalog_asset.ticker)
        return list((await self._db.execute(statement)).scalars().all())

    async def get(self, asset_id: UUID) -> AssetModel:
        statement = select(catalog_asset).where(catalog_asset.id == asset_id)
        model = (await self._db.execute(statement)).scalar_one_or_none()
        if model is None:
            raise AssetNotFoundError()
        return model

    async def upsert_many(self, assets: list[AdminAssetItem]) -> list[AssetModel]:
        models = []
        try:
            # Consistent lock order prevents overlapping batches from deadlocking.
            existing_models = list((await self._db.scalars(
                select(catalog_asset)
                .where(catalog_asset.ticker.in_([item.ticker for item in assets]))
                .order_by(catalog_asset.id)
                .with_for_update(of=AssetModel)
                .execution_options(populate_existing=True)
            )).all())
            by_ticker = {model.ticker: model for model in existing_models}
            for asset_data in assets:
                existing = by_ticker.get(asset_data.ticker)
                if existing is not None and existing.type_column != asset_data.type:
                    raise InvalidAssetQuoteMetadataError("Tipo de ativo existente não pode ser alterado")
                domain_asset = _domain_asset_from_admin_item(asset_data)
                if existing is None:
                    model = AssetMapper.to_model(domain_asset)
                    _apply_quote_metadata(model, asset_data, new=True)
                    self._db.add(model)
                    by_ticker[asset_data.ticker] = model
                else:
                    previous_currency = existing.quote_currency
                    _apply_quote_metadata(existing, asset_data, new=False)
                    if previous_currency != existing.quote_currency:
                        # Do not flush the proposed change before checking history.
                        with self._db.no_autoflush:
                            has_transactions = await self._db.scalar(
                                select(TransactionModel.id_transaction)
                                .where(TransactionModel.asset_id == existing.id).limit(1)
                            )
                        if has_transactions is not None:
                            raise AssetCurrencyLockedError()
                    model = AssetMapper.to_model(domain_asset, model=existing)
                models.append(model)
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise AssetAlreadyExistsError()
        except BaseException:
            await self._db.rollback()
            raise
        for model in models:
            await self._db.refresh(model)
        return models


def _apply_quote_metadata(model: AssetModel, data: QuoteMetadata, *, new: bool) -> None:
    # Omitted fields preserve configuration on legacy administrative upserts.
    for field in ("price_provider", "external_price_id", "quote_currency"):
        if field in data.model_fields_set:
            setattr(model, field, getattr(data, field))
    implied_currency = {"national_stock": "BRL", "international_stock": "USD"}.get(model.type_column)
    if new and "quote_currency" not in data.model_fields_set:
        model.quote_currency = implied_currency
    if implied_currency is not None and model.quote_currency != implied_currency:
        raise InvalidAssetQuoteMetadataError(f"Moeda incompatível com o tipo de ativo: esperada {implied_currency}")
    if model.price_provider == "brapi":
        if model.type_column not in {"national_stock", "real_estate_fund"} or model.quote_currency != "BRL":
            raise InvalidAssetQuoteMetadataError("brapi exige ação nacional ou FII com moeda BRL")
        if model.external_price_id is None or re.fullmatch(r"[A-Z0-9]+", model.external_price_id) is None:
            raise InvalidAssetQuoteMetadataError("Informe um símbolo brapi válido, com letras maiúsculas e números")
    elif model.external_price_id is not None:
        raise InvalidAssetQuoteMetadataError("Identificador externo exige um provedor de mercado")



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
