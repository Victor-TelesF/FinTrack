from abc import ABC, abstractmethod
from decimal import Decimal
from ..exceptions import InvalidValueError, InvalidPriceError

class Asset(ABC):
    def __init__(self, name: str, ticker: str, current_price: Decimal):

        
        if not isinstance(name, str) or not name:
            raise InvalidValueError("Nome deve ser uma string não vazia")
        
        if name.strip() == "":
            raise InvalidValueError("Nome deve ser uma string não vazia")
        
        name_validation = name.strip()
        self._name = name_validation

        
        if not isinstance(ticker, str) or not ticker:
            raise InvalidValueError("ticker deve ser uma string não vazia")
        
        if ticker.strip() == "":
            raise InvalidValueError("ticker deve ser uma string não vazia")
        
        ticker_validation = ticker.strip()

        self._ticker = ticker_validation

        self.current_price = current_price

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def ticker(self) -> str:
        return self._ticker
    
    @property
    def current_price(self) -> Decimal:
        return self._current_price
    
    @current_price.setter
    def current_price(self, value: Decimal) -> None:
        if not isinstance(value, Decimal):
            raise InvalidValueError("Use Decimal, não float")
        if value <= 0:
            raise InvalidPriceError("Preço não pode ser zero ou negativo")
        self._current_price = value

    @abstractmethod
    def calculate_return(self) -> Decimal:
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(ticker={self._ticker}, current_price={self._current_price})"
