from .variable_income import VariableIncome
from decimal import Decimal
import warnings
from ...exceptions import InvalidValueError
from ...return_context import ReturnContext


class RealEstateFund(VariableIncome):
    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)


    def _compute_return(self, context: ReturnContext) -> Decimal:
        
        if not isinstance(context.dividends_received, Decimal):
            raise InvalidValueError("Dividendos recebidos deve ser Decimal, não float")
        if context.dividends_received < 0:
            warnings.warn("Dividendos recebidos negativos — situação incomum, verifique os dados")

        rentabilidade_cota = super()._compute_return(context)
        rentabilidade_dividendos = context.dividends_received / context.purchase_price
        return rentabilidade_cota + rentabilidade_dividendos