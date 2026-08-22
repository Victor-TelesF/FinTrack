from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from uuid import UUID
from domain.enums import BondIndexType, IndexType, LiquidityType

class AssetBaseCreate(BaseModel):

    name: str
    ticker: str
    current_price: Decimal
    

class AssetBaseRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    ticker: str
    current_price: Decimal


class AssetCatalogRead(AssetBaseRead):
    asset_type: str
    rate: Decimal | None = None
    maturity_date: date | None = None
    fgc_covered: bool | None = None
    liquidity_type: LiquidityType | None = None
    index_type: IndexType | None = None
    bond_index_type: BondIndexType | None = None


class AdminAssetItem(BaseModel):
    type: Literal[
        "cdb", "government_bond", "national_stock", "international_stock",
        "real_estate_fund", "cryptocurrency",
    ]
    name: str
    ticker: str
    current_price: Decimal
    rate: Decimal | None = None
    maturity_date: date | None = None
    fgc_covered: bool | None = None
    liquidity_type: LiquidityType | None = None
    index_type: IndexType | None = None
    bond_index_type: BondIndexType | None = None


class AdminAssetUpsertRequest(BaseModel):
    assets: list[AdminAssetItem]