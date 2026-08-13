from decimal import Decimal
from typing import List
import httpx

from domain.protocols import PriceRequest, PriceSource
from app.price_sources.exceptions import PriceProviderError


class CoinGeckoSource(PriceSource):
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    def is_configured(self) -> bool:
        # CoinGecko public endpoints work without API key for simple price
        return True

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        prices = await self.get_latest_prices([request])
        if request.ticker not in prices:
            raise KeyError(f"Preço não disponível para o ticker {request.ticker}")
        return prices[request.ticker]

    async def get_latest_prices(self, requests: List[PriceRequest]) -> dict[str, Decimal]:
        ids = ",".join([r.external_price_id for r in requests if r.external_price_id])
        try:
            resp = await self._client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ids, "vs_currencies": "usd"},
            )
            resp.raise_for_status()
            data = resp.json()
            result = {}
            for r in requests:
                eid = r.external_price_id
                if not eid:
                    continue
                info = data.get(eid)
                if info and "usd" in info:
                    result[r.ticker] = Decimal(str(info["usd"]))
            return result
        except Exception as exc:
            raise PriceProviderError(str(exc)) from exc
