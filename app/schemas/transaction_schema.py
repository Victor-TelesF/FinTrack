from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date
from domain.enums import TransactionType
from .asset_schema import AssetBaseRead
from uuid import UUID


class TransactionCreate(BaseModel):

    ticker: str
    quantity: Decimal
    price: Decimal
    transaction_date: date


class TransactionRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id_transaction: UUID
    asset: AssetBaseRead
    quantity: Decimal
    price: Decimal
    transaction_type: TransactionType
    transaction_date: date