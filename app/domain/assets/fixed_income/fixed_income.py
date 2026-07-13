from decimal import Decimal
from ..asset import Asset
from datetime import date
from ...exceptions import InvalidRateError, InvalidMaturityError
from ...reference_date import reference_date

class FixedIncome(Asset):
    def __init__(self, name: str, ticker: str, current_price: Decimal, rate: Decimal, maturity_date: date):
        super().__init__(name, ticker, current_price)
        self.rate = rate
        self.maturity_date = maturity_date

    @property
    def rate(self) -> Decimal:
        return self._rate
    
    @property
    def maturity_date(self) -> date:
        return self._maturity_date
    
    @staticmethod
    def real_rate(nominal_rate: Decimal, inflation: Decimal) -> Decimal:
        if not isinstance(nominal_rate, Decimal):
            raise InvalidRateError("Taxa nominal deve ser Decimal, não float")
        if nominal_rate <= 0:
            raise InvalidRateError("Taxa nominal nao pode ser zero ou negativo")
        
        if not isinstance(inflation, Decimal):
            raise InvalidRateError("Inflação deve ser Decimal, não float")
        
        taxa_real = ((1 + nominal_rate) / (1 + inflation)) - 1
        
        return taxa_real
    
    @maturity_date.setter
    def maturity_date(self, data: date) -> None:
        if not isinstance(data, date):
            raise InvalidMaturityError("Data de vencimento deve ser do tipo date")
        if data <= reference_date():
            raise InvalidMaturityError()
        
        self._maturity_date = data

    @rate.setter
    def rate(self, value: Decimal) -> None:
        if not isinstance(value, Decimal):
            raise InvalidRateError("Taxa deve ser Decimal, não float")
        if value <= 0:
            raise InvalidRateError("Taxa não pode ser zero ou negativo")
        
        self._rate = value
