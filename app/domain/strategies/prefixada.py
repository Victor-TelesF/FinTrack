from decimal import Decimal
from ..return_context import ReturnContext

class FixedRateStrategy:
    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        return rate
    
