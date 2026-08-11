"""Define the fixed income asset base class.

This module contains the FixedIncome asset implementation that extends the
base Asset class with rate and maturity validation.
"""

from decimal import Decimal
from ..asset import Asset
from datetime import date
from ...exceptions import InvalidRateError, InvalidMaturityError
from ...reference_date import reference_date


class FixedIncome(Asset):
    """Represents a fixed income asset with rate and maturity date.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
        rate (Decimal): The fixed income rate.
        maturity_date (date): The maturity date of the asset.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal, rate: Decimal, maturity_date: date):
        super().__init__(name, ticker, current_price)
        self.rate = rate
        self.maturity_date = maturity_date

    @property
    def rate(self) -> Decimal:
        """Return the fixed income rate.

        Returns:
            Decimal: The asset rate.
        """
        return self._rate
    
    @property
    def maturity_date(self) -> date:
        """Return the asset maturity date.

        Returns:
            date: The maturity date.
        """
        return self._maturity_date
    
    @staticmethod
    def real_rate(nominal_rate: Decimal, inflation: Decimal) -> Decimal:
        """Calculate the real rate given nominal rate and inflation.

        Args:
            nominal_rate (Decimal): The nominal rate.
            inflation (Decimal): The inflation rate.

        Returns:
            Decimal: The calculated real rate.

        Raises:
            InvalidRateError: If nominal_rate or inflation is not a Decimal or if
                nominal_rate is less than or equal to zero.
        """
        if not isinstance(nominal_rate, Decimal):
            raise InvalidRateError("Taxa nominal deve ser Decimal, não float")
        if nominal_rate <= 0:
            raise InvalidRateError("Taxa nominal nao pode ser zero ou negativo")
        
        if not isinstance(inflation, Decimal):
            raise InvalidRateError("Inflação deve ser Decimal, não float")
        if inflation == Decimal("-1"):
            raise InvalidRateError("Inflação não pode ser igual a -1")
        
        taxa_real = ((1 + nominal_rate) / (1 + inflation)) - 1
        
        return taxa_real
    
    @maturity_date.setter
    def maturity_date(self, data: date) -> None:
        """Set the maturity date for the asset.

        Args:
            data (date): The maturity date.

        Raises:
            InvalidMaturityError: If data is not a date or if it is not after
                the reference date.
        """
        if not isinstance(data, date):
            raise InvalidMaturityError("Data de vencimento deve ser do tipo date")
        if data <= reference_date():
            raise InvalidMaturityError()
        
        self._maturity_date = data

    @rate.setter
    def rate(self, value: Decimal) -> None:
        """Set the rate for the fixed income asset.

        Args:
            value (Decimal): The rate value.

        Raises:
            InvalidRateError: If value is not a Decimal or if it is less than or
                equal to zero.
        """
        if not isinstance(value, Decimal):
            raise InvalidRateError("Taxa deve ser Decimal, não float")
        if value <= 0:
            raise InvalidRateError("Taxa não pode ser zero ou negativo")
        
        self._rate = value
