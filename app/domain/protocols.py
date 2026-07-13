"""Define reusable protocol interfaces for strategies and data sources.

This module contains runtime-checkable protocol definitions for the
return strategy and price source abstractions.
"""

from typing import Protocol, runtime_checkable
from decimal import Decimal
from .return_context import ReturnContext


@runtime_checkable
class ReturnStrategy(Protocol):
    """Protocol for return calculation strategies."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        """Calculate a return based on a rate and return context.

        Args:
            rate (Decimal): The rate used for the calculation.
            context (ReturnContext): The calculation context.

        Returns:
            Decimal: The calculated return.
        """
        ...


@runtime_checkable
class PriceSource(Protocol):
    """Protocol for price source data providers."""

    def get_latest_price(self, ticker: str) -> Decimal:
        """Get the latest price for the given ticker.

        Args:
            ticker (str): The asset ticker symbol.

        Returns:
            Decimal: The latest market price.
        """
        ...
