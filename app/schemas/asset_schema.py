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
    external_price_id: str | None = None
    current_price: Decimal
    rate: Decimal | None = None
    maturity_date: date | None = None
    fgc_covered: bool | None = None
    liquidity_type: LiquidityType | None = None
    index_type: IndexType | None = None
    bond_index_type: BondIndexType | None = None

    from pydantic import model_validator

    @model_validator(mode="after")
    def _require_price_id_for_crypto(self):
        if self.type == "cryptocurrency" and not self.external_price_id:
            raise ValueError(
                "cryptocurrency requer external_price_id explícito (id do CoinGecko, ex: 'bitcoin') — "
                "símbolos como 'ETH' ou 'LUNA' são ambíguos entre moedas diferentes e não podem ser "
                "resolvidos automaticamente sem risco de pegar o preço da moeda errada"
            )
        return self


class AdminAssetUpsertRequest(BaseModel):
    assets: list[AdminAssetItem]