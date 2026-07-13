from ..asset import Asset
from decimal import Decimal
from ...return_context import ReturnContext
from ...exceptions import InvalidPurchasePriceError
from abc import abstractmethod

class VariableIncome(Asset):
    def __init__(self, name: str, ticker: str, current_price: Decimal):
        super().__init__(name, ticker, current_price)
        if type(self) is VariableIncome:
            raise TypeError("VariableIncome é uma classe abstrata e não pode ser instanciada diretamente")

    def calculate_return(self, context: ReturnContext) -> Decimal:
        if not isinstance(context.purchase_price, Decimal):
            raise InvalidPurchasePriceError("Preço de compra deve ser Decimal, não float")
        if context.purchase_price <= 0:
            raise InvalidPurchasePriceError("Preço de compra não pode ser zero ou negativo")
        return self._compute_return(context)
        
    def _compute_return(self, context: ReturnContext) -> Decimal:
        return (self.current_price - context.purchase_price) / context.purchase_price