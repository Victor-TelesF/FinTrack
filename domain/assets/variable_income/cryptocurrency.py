"""Define the cryptocurrency asset type.

This module contains the Cryptocurrency implementation as a variable income asset.
"""

from .variable_income import VariableIncome
from decimal import Decimal
from ...exceptions import InvalidPurchasePriceError
from ...return_context import ReturnContext


class Cryptocurrency(VariableIncome):
    """Represents a cryptocurrency asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)