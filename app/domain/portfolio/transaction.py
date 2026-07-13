from decimal import Decimal
from ..enums import TransactionType
from ..assets import Asset
from ..reference_date import reference_date
from datetime import date
from uuid import uuid4
from ..exceptions import InvalidQuantityError, InvalidPriceError, InvalidTransactionTypeError, InvalidTransactionDateError, InvalidValueError


class Transaction():
    def __init__(self,asset: Asset, quantity: Decimal,
                price: Decimal, transaction_type: TransactionType,
                transaction_date: date):
        
        self._id_transaction = uuid4()
        self.asset = asset
        self.quantity = quantity
        self.price = price
        self.transaction_type = transaction_type
        self.transaction_date = transaction_date

    @property
    def id_transaction(self):
        return self._id_transaction

    @property
    def asset(self) -> Asset:
        return self._asset
    
    @property
    def quantity(self) -> Decimal:
        return self._quantity
    
    @property
    def price(self) -> Decimal:
        return self._price
    
    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type
    
    @property
    def transaction_date(self) -> date:
        return self._transaction_date
    
    @asset.setter
    def asset(self,value) -> None:
        if not isinstance(value, Asset):
            raise InvalidValueError("Asset deve ser uma instância de Asset")
        self._asset = value
    
    @quantity.setter
    def quantity(self, quantity: Decimal) -> None:
        if not isinstance(quantity, Decimal):
            raise InvalidQuantityError("Quantidade da transação tem que ser Decimal, não float")

        if quantity <= 0:
            raise InvalidQuantityError("Quantidade da transação não pode ser zero ou negativo")
        
        self._quantity = quantity

    @price.setter
    def price(self, price: Decimal) -> None:
        if not isinstance(price, Decimal):
            raise InvalidPriceError("Preço da transação tem que ser Decimal")
        
        if price <= 0:
            raise InvalidPriceError("Preço da transação não pode ser menor ou igual a zero")
        
        self._price = price

    @transaction_type.setter
    def transaction_type(self, value: TransactionType) -> None:
        if not isinstance(value, TransactionType):
            raise InvalidTransactionTypeError("Tipo de transação invalida")
        
        self._transaction_type = value

    @transaction_date.setter
    def transaction_date(self, value: date) -> None:
        if not isinstance(value, date):
            raise InvalidTransactionDateError("Data de transação tem que ser do tipo date")
        if value > reference_date():
            raise InvalidTransactionDateError("Data de transação não pode ser maior que hoje")
    
        self._transaction_date = value