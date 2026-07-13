"""Define the CDB asset and its return logic.

This module contains the implementation of CDB as a fixed-income asset
that uses specific index types and liquidity rules to calculate return.
"""

from decimal import Decimal
from .fixed_income import FixedIncome
from datetime import date
from ...exceptions import InvalidLiquidityError, InvalidIndexTypeError
from ...enums import LiquidityType, IndexType
from ...return_context import ReturnContext
from ...strategies.registry import get_strategy_for


class CDB(FixedIncome):
    """Represents a Certificate of Deposit (CDB) asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
        rate (Decimal): The contracted CDB rate.
        maturity_date (date): The asset maturity date.
        fgc_covered (bool): Whether the asset is covered by FGC.
        liquidity_type (LiquidityType): The asset liquidity type.
        index_type (IndexType): The asset index type.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal, 
                 rate: Decimal, maturity_date: date, fgc_covered: bool, 
                 liquidity_type: LiquidityType, index_type: IndexType):
        super().__init__(name, ticker, current_price, rate, maturity_date)

        self._fgc_covered = fgc_covered
        self.liquidity_type = liquidity_type
        self.index_type = index_type
        self._strategy = get_strategy_for(index_type)

    @property
    def fgc_covered(self) -> bool:
        """Return whether the asset is covered by FGC.

        Returns:
            bool: True if the asset is covered by FGC, otherwise False.
        """
        return self._fgc_covered
        
    @property
    def liquidity_type(self) -> LiquidityType:
        """Return the liquidity type of the CDB.

        Returns:
            LiquidityType: The liquidity classification of the asset.
        """
        return self._liquidity_type
    
    @property
    def index_type(self) -> IndexType:
        """Return the index type used by the CDB.

        Returns:
            IndexType: The index type of the asset.
        """
        return self._index_type
    
    @liquidity_type.setter
    def liquidity_type(self, value: LiquidityType) -> None:
        """Set the liquidity type for the CDB.

        Args:
            value (LiquidityType): The liquidity type to set.

        Raises:
            InvalidLiquidityError: If the value is not a valid LiquidityType.
        """
        if not isinstance(value, LiquidityType):
            raise InvalidLiquidityError("Valor de liquidez incorreto")
        self._liquidity_type = value
        
    @index_type.setter
    def index_type(self, value: IndexType) -> None:
        """Set the index type for the CDB.

        Args:
            value (IndexType): The index type to set.

        Raises:
            InvalidIndexTypeError: If the value is not a valid IndexType.
        """
        if not isinstance(value, IndexType):
            raise InvalidIndexTypeError("Valor de indexador incorreto")
        self._index_type = value
        self._strategy = get_strategy_for(value)

    def calculate_return(self, context: ReturnContext) -> Decimal:
        """Calculate the return for the CDB.

        Args:
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The calculated return value.
        """
        calculo = self._strategy.calculate(self.rate, context)
        return calculo