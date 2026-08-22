from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.mappers.asset_mapper import AssetMapper, UnsupportedAssetTypeError
from app.models.asset_model import AssetModel
from app.models.fixed_income_model import CDBModel, GovernmentBondModel
from app.models.variable_income_model import (
    CryptocurrencyModel,
    InternationalStockModel,
    NationalStockModel,
    RealEstateFundModel,
)
from domain.assets.fixed_income.cdb import CDB
from domain.assets.fixed_income.government_bond import GovernmentBond
from domain.assets.variable_income.cryptocurrency import Cryptocurrency
from domain.assets.variable_income.international_stock import InternationalStock
from domain.assets.variable_income.national_stock import NationalStock
from domain.assets.variable_income.real_estate_fund import RealEstateFund
from domain.enums import BondIndexType, IndexType, LiquidityType


PRICE = Decimal("100.25")
RATE = Decimal("0.12")
MATURITY = date(2030, 1, 1)


@pytest.mark.parametrize(
    ("asset", "model_type"),
    [
        (CDB("CDB", "CDB1", PRICE, RATE, MATURITY, True, LiquidityType.DIARIA, IndexType.CDI), CDBModel),
        (GovernmentBond("Tesouro", "T2029", PRICE, RATE, MATURITY, LiquidityType.DIARIA, BondIndexType.SELIC), GovernmentBondModel),
        (NationalStock("Empresa", "ABCD3", PRICE), NationalStockModel),
        (InternationalStock("Company", "COMP", PRICE), InternationalStockModel),
        (RealEstateFund("Fundo", "FUND11", PRICE), RealEstateFundModel),
        (Cryptocurrency("Bitcoin", "BTC", PRICE), CryptocurrencyModel),
    ],
)
def test_to_model_maps_concrete_asset_types(asset, model_type):
    asset_id = uuid4()

    model = AssetMapper.to_model(asset, asset_id=asset_id)

    assert isinstance(model, model_type)
    assert model.id == asset_id
    assert model.name == asset.name
    assert model.ticker == asset.ticker
    assert model.current_price == asset.current_price


@pytest.mark.parametrize(
    "model_type",
    [
        CDBModel,
        GovernmentBondModel,
        NationalStockModel,
        InternationalStockModel,
        RealEstateFundModel,
        CryptocurrencyModel,
    ],
)
def test_to_domain_maps_concrete_models(model_type):
    model = model_type()
    model.name = "Ativo"
    model.ticker = "ATV"
    model.current_price = PRICE

    if model_type in (CDBModel, GovernmentBondModel):
        model.rate = RATE
        model.maturity_date = MATURITY
        model.liquidity_type = LiquidityType.DIARIA
        if model_type is CDBModel:
            model.fgc_covered = True
            model.index_type = IndexType.CDI
        else:
            model.bond_index_type = BondIndexType.SELIC

    assert AssetMapper.to_domain(model).__class__ is not AssetModel


def test_to_domain_normalizes_enum_names_from_database():
    model = CDBModel()
    model.name = "CDB"
    model.ticker = "CDB1"
    model.current_price = PRICE
    model.rate = RATE
    model.maturity_date = MATURITY
    model.fgc_covered = True
    model.liquidity_type = "DIARIA"
    model.index_type = "CDI"

    asset = AssetMapper.to_domain(model)

    assert asset.liquidity_type is LiquidityType.DIARIA
    assert asset.index_type is IndexType.CDI


def test_to_model_updates_existing_model_without_changing_id():
    asset_id = uuid4()
    model = NationalStockModel()
    model.id = asset_id

    updated = AssetMapper.to_model(
        NationalStock("Empresa", "ABCD3", PRICE),
        model=model,
    )

    assert updated is model
    assert updated.id == asset_id


def test_to_model_rejects_unsupported_asset_type():
    class UnsupportedAsset:
        pass

    with pytest.raises(UnsupportedAssetTypeError):
        AssetMapper.to_model(UnsupportedAsset())