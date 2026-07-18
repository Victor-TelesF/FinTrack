"""Define the Selic return strategy implementation."""

from decimal import Decimal
from ..exceptions import SelicRateError
from ..return_context import ReturnContext


class SelicStrategy:
    """Calculate returns based on Selic market rates."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        """Calculate the return using the Selic rate from the return context.

        Args:
            rate (Decimal): The asset rate.
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The calculated Selic-based return.

        Raises:
            SelicRateError: If the Selic rate is missing from the context.
        """
        if context.market_rates is None or context.market_rates.selic_rate is None:
            raise SelicRateError()
        return rate * context.market_rates.selic_rate
