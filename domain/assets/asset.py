"""Domain base asset definitions.

This module defines the abstract base class for financial assets used
throughout the application.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from ..exceptions import InvalidValueError, InvalidPriceError


class Asset(ABC):
    """Abstract base class for a financial asset.

    Attributes:
        _name (str): Asset name.
        _ticker (str): Asset ticker symbol.
        _current_price (Decimal): Current asset price.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal):
        """Initialize an Asset instance.

        Args:
            name (str): The asset name.
            ticker (str): The asset ticker symbol.
            current_price (Decimal): The current price of the asset.

        Raises:
            InvalidValueError: If name or ticker is not a non-empty string, or if
                current_price is not a Decimal.
            InvalidPriceError: If current_price is less than or equal to zero.
        """

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
        """Return the asset name.

        Returns:
            str: The normalized asset name.
        """
        return self._name

    @property
    def ticker(self) -> str:
        """Return the asset ticker.

        Returns:
            str: The normalized asset ticker symbol.
        """
        return self._ticker

    @property
    def current_price(self) -> Decimal:
        """Return the current asset price.

        Returns:
            Decimal: The current price of the asset.
        """
        return self._current_price

    @current_price.setter
    def current_price(self, value: Decimal) -> None:
        """Set the current asset price.

        Args:
            value (Decimal): The new current price.

        Raises:
            InvalidValueError: If value is not a Decimal.
            InvalidPriceError: If value is less than or equal to zero.
        """
        if not isinstance(value, Decimal):
            raise InvalidValueError("Use Decimal, não float")
        if value <= 0:
            raise InvalidPriceError("Preço não pode ser zero ou negativo")
        self._current_price = value

    @abstractmethod
    def calculate_return(self) -> Decimal:
        """Calculate the asset return.

        Returns:
            Decimal: The calculated return for the asset.
        """
        ...

    def __repr__(self) -> str:
        """Return the developer representation of the asset.

        Returns:
            str: A string representation including ticker and current price.
        """
        return f"{self.__class__.__name__}(ticker={self._ticker}, current_price={self._current_price})"
