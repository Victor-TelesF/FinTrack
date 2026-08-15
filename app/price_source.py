from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssetModel
from domain.protocols import PriceRequest, PriceSource


class DatabasePriceSource(PriceSource):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        ticker = request.ticker
        statement = select(AssetModel.current_price).where(AssetModel.ticker == ticker)
        result = await self._db.execute(statement)
        price = result.scalar_one_or_none()
        if price is None:
            raise KeyError(f"Preço não disponível para o ticker {ticker}")
        return price

    async def get_latest_prices(self, requests: list[PriceRequest]) -> dict[str, Decimal]:
        tickers = [request.ticker for request in requests]
        statement = select(AssetModel.ticker, AssetModel.current_price).where(AssetModel.ticker.in_(tickers))
        result = await self._db.execute(statement)
        rows = result.all()
        return {ticker: price for ticker, price in rows}