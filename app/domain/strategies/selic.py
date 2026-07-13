from decimal import Decimal
from ..exceptions import SelicRateError
from ..return_context import ReturnContext

class SelicStrategy:
     def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        if context.market_rates is None or context.market_rates.selic_rate is None:
            raise SelicRateError()
        return rate * context.market_rates.selic_rate
