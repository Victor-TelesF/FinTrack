"""Define the portfolio entity and its operations.

This module contains the Portfolio class used to manage asset positions,
execute buy and sell transactions, and calculate portfolio metrics.
"""

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
    """Represents an investment portfolio.

    Args:
        wallet_id (str): The identifier for the portfolio wallet.
    """

    def __init__(self, wallet_id: str, id_portfolio: UUID | None = None):
        if not isinstance(wallet_id, str):
            raise InvalidValueError("Valor de wallet_id tem que ser str")
        self._wallet_id = wallet_id
        if id_portfolio is None:
            id_portfolio = uuid4()
        if not isinstance(id_portfolio, UUID):
            raise InvalidValueError("id_portfolio tem que ser UUID")
        self._id_portfolio = id_portfolio
        self._positions: dict[str, Position] = {}

    @property
    def wallet_id(self) -> str:
        """Return the portfolio wallet identifier.

        Returns:
            str: The wallet identifier.
        """
        return self._wallet_id

    @property
    def id_portfolio(self) -> UUID:
        """Return the portfolio unique identifier.

        Returns:
            UUID: The portfolio identifier.
        """
        return self._id_portfolio

    @property
    def positions(self) -> dict[str, Position]:
        """Return a copy of the portfolio positions.

        Returns:
            dict[str, Position]: The portfolio positions by ticker.
        """
        return self._positions.copy()
    
    def buy(
        self,
        asset: Asset,
        quantity: Decimal,
        price: Decimal,
        buy_date: date,
        transaction_sequence: int | None = None,
    ) -> Transaction:
        """Execute a buy transaction and update the portfolio position.

        Args:
            asset (Asset): The asset being purchased.
            quantity (Decimal): The quantity to buy.
            price (Decimal): The purchase price per unit.
            buy_date (date): The date of purchase.

        Returns:
            Transaction: The executed buy transaction.
        """
        transaction = Transaction(
            asset,
            quantity,
            price,
            TransactionType.BUY,
            buy_date,
            transaction_sequence,
        )
        if asset.ticker not in self._positions.keys():

            position = Position(asset)
            position.add_transaction(transaction)
            self._positions[asset.ticker] = position
        
        else:
            self._positions[asset.ticker].add_transaction(transaction)

        return transaction
    
    def sell(
        self,
        asset: Asset,
        quantity: Decimal,
        price: Decimal,
        sell_date: date,
        transaction_sequence: int | None = None,
    ) -> Transaction:
        """Execute a sell transaction and update the portfolio position.

        Args:
            asset (Asset): The asset being sold.
            quantity (Decimal): The quantity to sell.
            price (Decimal): The sale price per unit.
            sell_date (date): The date of sale.

        Returns:
            Transaction: The executed sell transaction.

        Raises:
            AssetNotFoundError: If the asset ticker is not present in the portfolio.
        """
        transaction = Transaction(
            asset,
            quantity,
            price,
            TransactionType.SELL,
            sell_date,
            transaction_sequence,
        )

        if asset.ticker not in self._positions.keys():
            raise AssetNotFoundError("Esse ticker nunca foi comprado nessa carteira")
        else:
            self._positions[asset.ticker].add_transaction(transaction)

        if self._positions[asset.ticker].quantity == Decimal("0"):
            self._positions.pop(asset.ticker)

        return transaction
    

    def get_total_cost(self) -> Decimal:
        """Return the total cost basis of the portfolio.

        Returns:
            Decimal: The total invested cost across all positions.
        """
        total = Decimal("0")
        for position in self._positions.values():
            total += position.quantity * position.average_price
    
        return total
    
    
    def get_total_equity(self, price_source: PriceSource) -> Decimal:
        """Return the total market value of the portfolio.

        Args:
            price_source (PriceSource): The source for latest market prices.

        Returns:
            Decimal: The total equity of the portfolio.
        """
        total = Decimal("0")
        for position in self._positions.values():
            total += position.quantity * price_source.get_latest_price(position.asset.ticker)
        
        return total
    
    def update_portfolio_prices(self, price_source: PriceSource) -> None:
        """Update current asset prices for all portfolio positions.

        Args:
            price_source (PriceSource): The source for latest market prices.
        """
        for ticker, position in self._positions.items():
            position.asset.current_price = price_source.get_latest_price(ticker)

    
    def get_total_pnl(self, price_source: PriceSource) -> Decimal:
        """Return the portfolio total profit and loss.

        Args:
            price_source (PriceSource): The source for latest market prices.

        Returns:
            Decimal: The total PnL for the portfolio.
        """
        return self.get_total_equity(price_source) - self.get_total_cost()
    
    def get_pnl(self, ticker: str, price_source: PriceSource) -> Decimal:
        """Return the profit and loss for a specific position.

        Args:
            ticker (str): The asset ticker.
            price_source (PriceSource): The source for latest market prices.

        Returns:
            Decimal: The position PnL.

        Raises:
            AssetNotFoundError: If the ticker is not present in the portfolio.
        """
        if ticker not in self._positions.keys():
            raise AssetNotFoundError("Esse ticker não existe")
        
        position = self._positions[ticker]
        current_price = price_source.get_latest_price(ticker)

        pnl = (position.quantity * current_price) - (position.quantity * position.average_price)

        return pnl