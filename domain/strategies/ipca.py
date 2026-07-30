"""Define the IPCA return strategy implementation."""

from ..exceptions import IpcaRateError
from decimal import Decimal
from ..return_context import ReturnContext


class IPCAStrategy:
    """Calculate returns based on IPCA market rates."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        """Calculate the return using the IPCA rate from the return context.

        Args:
            rate (Decimal): The asset rate.
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The calculated IPCA-based return.

        Raises:
            IpcaRateError: If the IPCA rate is missing from the context.
        """
        if context.market_rates is None or context.market_rates.ipca_rate is None:
            raise IpcaRateError()
        return rate + context.market_rates.ipca_rate
