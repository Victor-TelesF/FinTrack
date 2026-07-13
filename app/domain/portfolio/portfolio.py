from decimal import Decimal
from ..assets import Asset
from .position import Position
from .transaction import Transaction
from ..enums import TransactionType
from ..protocols import PriceSource
from ..exceptions import InsufficientBalanceError, InvalidValueError, AssetNotFoundError 
from uuid import uuid4, UUID
from datetime import date

class Portfolio:
    def __init__(self, wallet_id: str):
        if not isinstance(wallet_id, str):
            raise InvalidValueError("Valor de wallet_id tem que ser str")
        self._wallet_id = wallet_id

        self._id_portfolio = uuid4()
        self._positions: dict[str, Position] = {}

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def id_portfolio(self) -> UUID:
        return self._id_portfolio

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions.copy()
    
    def buy(self, asset: Asset, quantity: Decimal, price: Decimal, buy_date: date) -> Transaction:

        transaction = Transaction(asset, quantity, price, TransactionType.BUY, buy_date)
        if asset.ticker not in self._positions.keys():

            position = Position(asset)
            position.add_transaction(transaction)
            self._positions[asset.ticker] = position
        
        else:
            self._positions[asset.ticker].add_transaction(transaction)

        return transaction
    
    def sell(self, asset: Asset, quantity: Decimal, price: Decimal, sell_date: date) -> Transaction:

        transaction = Transaction(asset,quantity, price, TransactionType.SELL, sell_date)

        if asset.ticker not in self._positions.keys():
            raise AssetNotFoundError("Esse ticker nunca foi comprado nessa carteira")
        else:
            self._positions[asset.ticker].add_transaction(transaction)

        if self._positions[asset.ticker].quantity == Decimal("0"):
            self._positions.pop(asset.ticker)

        return transaction
    

    def get_total_cost(self) -> Decimal:
        total = Decimal("0")
        for position in self._positions.values():
            total += position.quantity * position.average_price
    
        return total
    
    
    def get_total_equity(self, price_source: PriceSource) -> Decimal:
        total = Decimal("0")
        for position in self._positions.values():
            total += position.quantity * price_source.get_latest_price(position.asset.ticker)
        
        return total
    
    def update_portfolio_prices(self, price_source: PriceSource) -> None:
        for ticker, position in self._positions.items():
            position.asset.current_price = price_source.get_latest_price(ticker)

    
    def get_total_pnl(self, price_source: PriceSource) -> Decimal:

        return self.get_total_equity(price_source) - self.get_total_cost()
    
    def get_pnl(self, ticker: str, price_source: PriceSource) -> Decimal:
        if ticker not in self._positions.keys():
            raise AssetNotFoundError("Esse ticker não existe")
        
        position = self._positions[ticker]
        current_price = price_source.get_latest_price(ticker)

        pnl = (position.quantity * current_price) - (position.quantity * position.average_price)

        return pnl