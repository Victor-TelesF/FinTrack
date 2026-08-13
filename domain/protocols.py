"""Define reusable protocol interfaces for strategies and data sources.

This module contains runtime-checkable protocol definitions for the
return strategy and price source abstractions.
"""

from typing import Protocol, runtime_checkable
from decimal import Decimal
from dataclasses import dataclass
from .return_context import ReturnContext


@runtime_checkable
class ReturnStrategy(Protocol):
    """Protocol for return calculation strategies."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        ...


@dataclass(frozen=True)
class PriceRequest:
    """Dados suficientes para um PriceSource resolver o preço sem ambiguidade."""

    ticker: str
    asset_type: str
    external_price_id: str | None


@runtime_checkable
class PriceSource(Protocol):
    """Protocol for price source data providers (async)."""

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        ...

    async def get_latest_prices(self, requests: list[PriceRequest]) -> dict[str, Decimal]:
        """Return a dict indexed by ticker."""
        ...
