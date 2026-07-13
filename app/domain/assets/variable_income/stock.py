"""Define the stock asset base class.

This module provides the Stock abstract base class for variable income
assets that require a currency implementation.
"""

from .variable_income import VariableIncome
from abc import abstractmethod
from decimal import Decimal
from ...return_context import ReturnContext
from ...enums import Currency


class Stock(VariableIncome):
    """Represents a stock asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)

    @property
    @abstractmethod
    def currency(self) -> Currency:
        """Return the currency used by the stock.

        Returns:
            Currency: The currency of the stock asset.
        """
        ...
        
