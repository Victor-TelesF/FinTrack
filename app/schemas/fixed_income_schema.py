from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date
from domain.enums import IndexType, BondIndexType, LiquidityType
from .asset_schema import AssetBaseRead, AssetBaseCreate


class CDBCreate(AssetBaseCreate):
    fgc_covered: bool
    liquidity_type: LiquidityType
    index_type: IndexType
    maturity_date: date
    rate: Decimal

class CDBRead(AssetBaseRead):

    fgc_covered: bool
    liquidity_type: LiquidityType
    index_type: IndexType
    maturity_date: date
    rate: Decimal

class GovernmentBondCreate(AssetBaseCreate):

    liquidity_type: LiquidityType
    bond_index_type: BondIndexType
    maturity_date: date
    rate: Decimal

class GovernmentBondRead(AssetBaseRead):
    
    liquidity_type: LiquidityType
    bond_index_type: BondIndexType
    maturity_date: date
    rate: Decimal