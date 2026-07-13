from ..exceptions import CdiRateError
from decimal import Decimal
from ..return_context import ReturnContext

class CDIStrategy:
    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        if context.market_rates is None or context.market_rates.cdi_rate is None:
            raise CdiRateError()
        return rate * context.market_rates.cdi_rate