from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssetModel
from domain.protocols import PriceSource


class DatabasePriceSource(PriceSource):

    def __init__(self, db: Session):
        self._db = db

    def get_latest_price(self, ticker: str) -> Decimal:
        statement = select(AssetModel.current_price).where(AssetModel.ticker == ticker)
        price = self._db.execute(statement).scalar_one_or_none()
        if price is None:
            raise KeyError(f"Preço não disponível para o ticker {ticker}")
        return price