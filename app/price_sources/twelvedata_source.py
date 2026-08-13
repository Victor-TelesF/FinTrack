from decimal import Decimal
from typing import List
import httpx

from domain.protocols import PriceRequest, PriceSource
from app.price_sources.exceptions import PriceProviderError


class TwelveDataSource(PriceSource):
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self._client = client
        self._api_key = api_key

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        prices = await self.get_latest_prices([request])
        if request.ticker not in prices:
            raise KeyError(f"Preço não disponível para o ticker {request.ticker}")
        return prices[request.ticker]

    async def get_latest_prices(self, requests: List[PriceRequest]) -> dict[str, Decimal]:
        try:
            result = {}
            for r in requests:
                symbol = r.external_price_id or r.ticker
                resp = await self._client.get(
                    "https://api.twelvedata.com/price",
                    params={"symbol": symbol, "apikey": self._api_key},
                )
                resp.raise_for_status()
                data = resp.json()
                if "price" in data:
                    result[r.ticker] = Decimal(str(data["price"]))
            return result
        except Exception as exc:
            raise PriceProviderError(str(exc)) from exc
