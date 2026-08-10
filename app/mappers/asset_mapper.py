from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.asset_model import AssetModel
from app.models.fixed_income_model import CDBModel, GovernmentBondModel
from app.models.variable_income_model import (
    CryptocurrencyModel,
    InternationalStockModel,
    NationalStockModel,
    RealEstateFundModel,
)
from domain.assets.asset import Asset
from domain.assets.fixed_income.cdb import CDB
from domain.assets.fixed_income.government_bond import GovernmentBond
from domain.assets.variable_income.cryptocurrency import Cryptocurrency
from domain.assets.variable_income.international_stock import InternationalStock
from domain.assets.variable_income.national_stock import NationalStock
from domain.assets.variable_income.real_estate_fund import RealEstateFund
from domain.enums import BondIndexType, IndexType, LiquidityType


class UnsupportedAssetTypeError(TypeError):
    """Raised when an ORM or domain asset type has no mapper."""


class AssetMapper:
    """Convert concrete asset models to and from domain entities."""

    @staticmethod
    def to_domain(model: AssetModel) -> Asset:
        common = {
            "name": model.name,
            "ticker": model.ticker,
            "current_price": model.current_price,
        }

        if isinstance(model, CDBModel):
            return CDB(
                **common,
                rate=model.rate,
                maturity_date=model.maturity_date,
                fgc_covered=model.fgc_covered,
                liquidity_type=_enum_value(model.liquidity_type, LiquidityType),
                index_type=_enum_value(model.index_type, IndexType),
            )
        if isinstance(model, GovernmentBondModel):
            return GovernmentBond(
                **common,
                rate=model.rate,
                maturity_date=model.maturity_date,
                liquidity_type=_enum_value(model.liquidity_type, LiquidityType),
                bond_index_type=_enum_value(model.bond_index_type, BondIndexType),
            )
        if isinstance(model, NationalStockModel):
            return NationalStock(**common)
        if isinstance(model, InternationalStockModel):
            return InternationalStock(**common)
        if isinstance(model, RealEstateFundModel):
            return RealEstateFund(**common)
        if isinstance(model, CryptocurrencyModel):
            return Cryptocurrency(**common)

        raise UnsupportedAssetTypeError(
            f"Modelo de ativo não suportado: {type(model).__name__}"
        )

    @staticmethod
    def to_model(
        asset: Asset,
        *,
        model: AssetModel | None = None,
        asset_id: UUID | None = None,
    ) -> AssetModel:
        model_type = _model_type_for(asset)
        if model is None:
            model = model_type()
        elif not isinstance(model, model_type):
            raise UnsupportedAssetTypeError(
                f"Modelo incompatível para {type(asset).__name__}: "
                f"{type(model).__name__}"
            )

        model.name = asset.name
        model.ticker = asset.ticker
        model.current_price = asset.current_price
        if asset_id is not None:
            model.id = asset_id

        if isinstance(asset, (CDB, GovernmentBond)):
            model.rate = asset.rate
            model.maturity_date = asset.maturity_date
            model.liquidity_type = asset.liquidity_type
            if isinstance(asset, CDB):
                model.fgc_covered = asset.fgc_covered
                model.index_type = asset.index_type
            else:
                model.bond_index_type = asset.bond_index_type

        return model


def _model_type_for(asset: Asset) -> type[AssetModel]:
    model_types = (
        (CDB, CDBModel),
        (GovernmentBond, GovernmentBondModel),
        (NationalStock, NationalStockModel),
        (InternationalStock, InternationalStockModel),
        (RealEstateFund, RealEstateFundModel),
        (Cryptocurrency, CryptocurrencyModel),
    )
    for domain_type, model_type in model_types:
        if isinstance(asset, domain_type):
            return model_type
    raise UnsupportedAssetTypeError(
        f"Ativo de domínio não suportado: {type(asset).__name__}"
    )


def _enum_value(value: Any, enum_type: type) -> Any:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            return enum_type[value]
    raise TypeError(f"Valor inválido para {enum_type.__name__}: {value!r}")