from ..exceptions import IpcaRateError
from decimal import Decimal
from ..return_context import ReturnContext

class IPCAStrategy:
    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        if context.market_rates is None or context.market_rates.ipca_rate is None:
            raise IpcaRateError()
        return rate + context.market_rates.ipca_rate
