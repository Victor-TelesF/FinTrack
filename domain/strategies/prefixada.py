"""Define the fixed-rate return strategy implementation."""

from decimal import Decimal
from ..return_context import ReturnContext


class FixedRateStrategy:
    """Calculate returns for fixed-rate assets."""

    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        """Calculate the return using a fixed rate.

        Args:
            rate (Decimal): The asset rate.
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The fixed return value.
        """
        return rate
    
