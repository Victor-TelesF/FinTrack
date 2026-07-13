from decimal import Decimal
from .fixed_income import FixedIncome
from datetime import date
from ...exceptions import InvalidLiquidityError, InvalidIndexTypeError
from ...enums import LiquidityType, IndexType
from ...return_context import ReturnContext
from ...strategies.registry import get_strategy_for

class CDB(FixedIncome):
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
        return self._fgc_covered
        
    @property
    def liquidity_type(self) -> LiquidityType:
        return self._liquidity_type
    
    @property
    def index_type(self) -> IndexType:
        return self._index_type
    
    @liquidity_type.setter
    def liquidity_type(self, value: LiquidityType) -> None:
        if not isinstance(value, LiquidityType):
            raise InvalidLiquidityError("Valor de liquidez incorreto")
        self._liquidity_type = value
        
    @index_type.setter
    def index_type(self, value: IndexType) -> None:
        if not isinstance(value, IndexType):
            raise InvalidIndexTypeError("Valor de indexador incorreto")
        self._index_type = value
        self._strategy = get_strategy_for(value)

    def calculate_return(self, context: ReturnContext) -> Decimal:
        calculo = self._strategy.calculate(self.rate, context)
        return calculo