"""Define the government bond asset and its return logic.

This module implements the GovernmentBond fixed-income asset, which uses a
bond-specific index type and liquidity classification for return calculations.
"""

from decimal import Decimal
from .fixed_income import FixedIncome
from datetime import date
from ...exceptions import InvalidLiquidityError, InvalidIndexTypeError
from ...enums import LiquidityType, BondIndexType
from ...return_context import ReturnContext
from ...strategies.registry import get_strategy_for


class GovernmentBond(FixedIncome):
    """Represents a government bond asset.

    Args:
        name (str): The asset name.
        ticker (str): The asset ticker symbol.
        current_price (Decimal): The current price of the asset.
        rate (Decimal): The asset rate.
        maturity_date (date): The asset maturity date.
        liquidity_type (LiquidityType): The asset liquidity type.
        bond_index_type (BondIndexType): The bond index type.
    """

    def __init__(self, name: str, ticker: str, current_price: Decimal, 
                rate: Decimal, maturity_date: date, liquidity_type: LiquidityType, 
                bond_index_type: BondIndexType):
        
        super().__init__(name, ticker, current_price, rate, maturity_date)
        
        self.liquidity_type = liquidity_type
        self.bond_index_type = bond_index_type
        self._strategy = get_strategy_for(bond_index_type)

    @property
    def liquidity_type(self) -> LiquidityType:
        """Return the liquidity type of the government bond.

        Returns:
            LiquidityType: The liquidity classification of the asset.
        """
        return self._liquidity_type
    
    @property
    def bond_index_type(self) -> BondIndexType:
        """Return the bond index type used by the asset.

        Returns:
            BondIndexType: The bond index type.
        """
        return self._bond_index_type
    
    @liquidity_type.setter
    def liquidity_type(self, value: LiquidityType) -> None:
        """Set the liquidity type for the government bond.

        Args:
            value (LiquidityType): The liquidity type to set.

        Raises:
            InvalidLiquidityError: If the value is not a valid LiquidityType.
        """
        if not isinstance(value, LiquidityType):
            raise InvalidLiquidityError("Valor de liquidez incorreto")
        self._liquidity_type = value
        
    @bond_index_type.setter
    def bond_index_type(self, value: BondIndexType) -> None:
        """Set the bond index type for the asset.

        Args:
            value (BondIndexType): The bond index type to set.

        Raises:
            InvalidIndexTypeError: If the value is not a valid BondIndexType.
        """
        if not isinstance(value, BondIndexType):
            raise InvalidIndexTypeError("Valor de indexador do tesouro incorreto")
        self._bond_index_type = value
        self._strategy = get_strategy_for(value)

    def calculate_return(self, context: ReturnContext) -> Decimal:
        """Calculate the return for the government bond.

        Args:
            context (ReturnContext): The return calculation context.

        Returns:
            Decimal: The calculated return value.
        """
        return self._strategy.calculate(self.rate, context)