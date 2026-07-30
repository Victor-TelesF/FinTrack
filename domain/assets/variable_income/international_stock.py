"""Define the international stock asset type.

This module contains the InternationalStock implementation for variable
income assets denominated in USD.
"""

from .stock import Stock
from decimal import Decimal
from ...enums import Currency


class InternationalStock(Stock):
    """Represents an international stock asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)
        
    @property
    def currency(self) -> Currency:
        """Return the currency used by the international stock.

        Returns:
            Currency: The currency for the asset, always USD.
        """
        return Currency.USD