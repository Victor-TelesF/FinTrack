from typing import Protocol, runtime_checkable
from decimal import Decimal
from .return_context import ReturnContext

@runtime_checkable
class ReturnStrategy(Protocol):
    def calculate(self, rate: Decimal, context: ReturnContext) -> Decimal:
        ...

@runtime_checkable
class PriceSource(Protocol):
    def get_latest_price(self, ticker: str) -> Decimal:
        ...
