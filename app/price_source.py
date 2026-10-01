from collections.abc import Mapping
from decimal import Decimal

from domain.protocols import PriceSource


class InMemoryPriceSource(PriceSource):
    """Synchronous price snapshot; all database I/O happens before evaluation."""

    def __init__(self, prices: Mapping[str, Decimal]):
        self._prices = dict(prices)

    def get_latest_price(self, ticker: str) -> Decimal:
        try:
            return self._prices[ticker]
        except KeyError:
            raise KeyError(f"Preço não disponível para o ticker {ticker}") from None
