from decimal import Decimal
from typing import List
import httpx

from domain.protocols import PriceRequest, PriceSource
from app.price_sources.exceptions import PriceProviderError


class BrapiSource(PriceSource):
    def __init__(self, client: httpx.AsyncClient, token: str):
        self._client = client
        self._token = token

    def is_configured(self) -> bool:
        return bool(self._token)

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        prices = await self.get_latest_prices([request])
        if request.ticker not in prices:
            raise KeyError(f"Preço não disponível para o ticker {request.ticker}")
        return prices[request.ticker]

    async def get_latest_prices(self, requests: List[PriceRequest]) -> dict[str, Decimal]:
        # Simple batch: use external_price_id or ticker
        ids = ",".join([r.external_price_id or r.ticker for r in requests])
        try:
            resp = await self._client.get(f"https://brapi.dev/api/quote/list?symbols={ids}")
            resp.raise_for_status()
            data = resp.json()
            # parse according to brapi's structure; keep simple mapping by ticker
            result = {}
            for item in data.get("results", []):
                ticker = item.get("symbol")
                price = item.get("regularMarketPrice")
                if ticker and price is not None:
                    result[ticker] = Decimal(str(price))
            return result
        except Exception as exc:
            raise PriceProviderError(str(exc)) from exc
