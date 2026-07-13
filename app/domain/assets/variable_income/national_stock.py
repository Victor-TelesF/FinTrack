from .stock import Stock
from decimal import Decimal
from ...enums import Currency

class NationalStock(Stock):
    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)

    @property
    def currency(self) -> Currency:
        return Currency.BRL