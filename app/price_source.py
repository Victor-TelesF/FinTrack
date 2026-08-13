from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssetModel
from domain.protocols import PriceSource


class DatabasePriceSource(PriceSource):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_latest_price(self, ticker: str) -> Decimal:
        statement = select(AssetModel.current_price).where(AssetModel.ticker == ticker)
        result = await self._db.execute(statement)
        price = result.scalar_one_or_none()
        if price is None:
            raise KeyError(f"Preço não disponível para o ticker {ticker}")
        return price

    async def get_latest_prices(self, tickers: list[str]) -> dict[str, Decimal]:
        statement = select(AssetModel.ticker, AssetModel.current_price).where(AssetModel.ticker.in_(tickers))
        result = await self._db.execute(statement)
        rows = result.all()
        return {ticker: price for ticker, price in rows}