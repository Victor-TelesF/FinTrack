"""Define the variable income asset base class.

This module contains the VariableIncome implementation for assets whose
return is based on purchase price and current price performance.
"""

from ..asset import Asset
from decimal import Decimal
from ...return_context import ReturnContext
from ...exceptions import InvalidPurchasePriceError
from abc import abstractmethod


class VariableIncome(Asset):
    """Represents a variable income asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)
        if type(self) is VariableIncome:
            raise TypeError("VariableIncome é uma classe abstrata e não pode ser instanciada diretamente")

    def calculate_return(self, context: ReturnContext) -> Decimal:
        """Calculate the return based on purchase price and current price.

        Args:
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The computed return value.

        Raises:
            InvalidPurchasePriceError: If purchase_price is not Decimal or is less
                than or equal to zero.
        """
        if not isinstance(context.purchase_price, Decimal):
            raise InvalidPurchasePriceError("Preço de compra deve ser Decimal, não float")
        if context.purchase_price <= 0:
            raise InvalidPurchasePriceError("Preço de compra não pode ser zero ou negativo")
        return self._compute_return(context)
        
    def _compute_return(self, context: ReturnContext) -> Decimal:
        """Compute the base return for variable income assets.

        Args:
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The base price return.
        """
        return (self.current_price - context.purchase_price) / context.purchase_price