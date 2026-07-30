"""Define the real estate fund asset type.

This module contains the RealEstateFund implementation for variable income assets
that include dividend returns in addition to unit performance.
"""

from .variable_income import VariableIncome
from decimal import Decimal
import warnings
from ...exceptions import InvalidValueError
from ...return_context import ReturnContext


class RealEstateFund(VariableIncome):
    """Represents a real estate fund asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)

    def _compute_return(self, context: ReturnContext) -> Decimal:
        """Compute the return for the real estate fund.

        Args:
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The combined return from unit performance and dividends.

        Raises:
            InvalidValueError: If context.dividends_received is not a Decimal.
        """
        if not isinstance(context.dividends_received, Decimal):
            raise InvalidValueError("Dividendos recebidos deve ser Decimal, não float")
        if context.dividends_received < 0:
            warnings.warn("Dividendos recebidos negativos — situação incomum, verifique os dados")

        rentabilidade_cota = super()._compute_return(context)
        rentabilidade_dividendos = context.dividends_received / context.purchase_price
        return rentabilidade_cota + rentabilidade_dividendos