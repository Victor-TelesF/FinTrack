from decimal import Decimal
from .fixed_income import FixedIncome
from datetime import date
from ...exceptions import InvalidLiquidityError, InvalidIndexTypeError
from ...enums import LiquidityType, BondIndexType
from ...return_context import ReturnContext
from ...strategies.registry import get_strategy_for

class GovernmentBond(FixedIncome):
    def __init__(self, name: str, ticker: str, current_price: Decimal, 
                rate: Decimal, maturity_date: date, liquidity_type: LiquidityType, 
                bond_index_type: BondIndexType):
        
        super().__init__(name, ticker, current_price, rate, maturity_date)
        
        self.liquidity_type = liquidity_type
        self.bond_index_type = bond_index_type
        self._strategy = get_strategy_for(bond_index_type)

    @property
    def liquidity_type(self) -> LiquidityType:
        return self._liquidity_type
    
    @property
    def bond_index_type(self) -> BondIndexType:
        return self._bond_index_type
    
    @liquidity_type.setter
    def liquidity_type(self, value: LiquidityType) -> None:
        if not isinstance(value, LiquidityType):
            raise InvalidLiquidityError("Valor de liquidez incorreto")
        self._liquidity_type = value
        
    @bond_index_type.setter
    def bond_index_type(self, value: BondIndexType) -> None:
        if not isinstance(value, BondIndexType):
            raise InvalidIndexTypeError("Valor de indexador do tesouro incorreto")
        self._bond_index_type = value
        self._strategy = get_strategy_for(value)

    def calculate_return(self, context: ReturnContext) -> Decimal:
        return self._strategy.calculate(self.rate, context)