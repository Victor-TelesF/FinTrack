from .variable_income import VariableIncome
from decimal import Decimal
from ...exceptions import InvalidPurchasePriceError
from ...return_context import ReturnContext

class Cryptocurrency(VariableIncome):
    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)