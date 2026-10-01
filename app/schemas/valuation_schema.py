from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValuationAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    ticker: str
    asset_type: str
    registered_price: Decimal = Field(
        validation_alias="current_price",
        description="Preço cadastrado; a avaliação utiliza quote.price.",
    )


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: UUID
    price: Decimal
    currency: str
    source: Literal["brapi", "manual"]
    quoted_at: datetime | None = Field(description="Horário da fonte; null quando desconhecido.")
    fetched_at: datetime = Field(description="Horário de obtenção; não indica idade da cotação.")
    from_cache: bool


class PositionValuationRead(BaseModel):
    asset: ValuationAssetRead
    quantity: Decimal
    average_price: Decimal
    cost_basis: Decimal
    market_value: Decimal
    pnl: Decimal
    return_percentage: Decimal
    currency: str
    quote: QuoteRead


class CurrencyTotalRead(BaseModel):
    currency: str
    total_cost: Decimal
    total_equity: Decimal
    total_pnl: Decimal
    return_percentage: Decimal
    contains_manual_prices: bool


class PortfolioValuationRead(BaseModel):
    totals_by_currency: list[CurrencyTotalRead]
    contains_manual_prices: bool
    quotes: list[QuoteRead]


class ValuationErrorRead(BaseModel):
    detail: str
    asset_ids: list[UUID]
