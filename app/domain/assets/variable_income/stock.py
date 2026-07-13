from .variable_income import VariableIncome
from abc import abstractmethod
from decimal import Decimal
from ...return_context import ReturnContext
from ...enums import Currency

class Stock(VariableIncome):
    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)

    @property
    @abstractmethod
    def currency(self) -> Currency:
        ...
        
