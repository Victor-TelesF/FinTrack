"""Define the CDI return strategy implementation."""

from ..exceptions import CdiRateError
from decimal import Decimal
from ..return_context import ReturnContext


class CDIStrategy:
    """Calculate returns based on CDI market rates."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        """Calculate the return using the CDI rate from the return context.

        Args:
            rate (Decimal): The asset rate.
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The calculated CDI-based return.

        Raises:
            CdiRateError: If the CDI rate is missing from the context.
        """
        if context.market_rates is None or context.market_rates.cdi_rate is None:
            raise CdiRateError()
        return rate * context.market_rates.cdi_rate