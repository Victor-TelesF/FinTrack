from pydantic import BaseModel, ConfigDict
from uuid import UUID
from decimal import Decimal
from .asset_schema import AssetBaseRead


class PortfolioRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)
    id_portfolio: UUID


class PositionRead(BaseModel):
    asset: AssetBaseRead
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    cost_basis: Decimal
    market_value: Decimal
    pnl: Decimal
    return_percentage: Decimal


class PortfolioSummaryRead(BaseModel):
    total_cost: Decimal
    total_equity: Decimal
    total_pnl: Decimal
    return_percentage: Decimal