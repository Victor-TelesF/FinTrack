"""Define portfolio positions and transaction aggregation.

This module contains the Position entity, which tracks a portfolio asset and
its transactions while providing quantity and average price calculations.
"""

from ..assets import Asset
from .transaction import Transaction
from ..enums import TransactionType
from decimal import Decimal
from ..exceptions import InvalidValueError, InsufficientBalanceError


class Position:
    """Represents a position for a portfolio asset.

    Args:
        asset (Asset): The asset associated with this position.
        transaction_list (list[Transaction], optional): Initial transactions.
    """

    def __init__(self, asset: Asset, transaction_list: list[Transaction] = None ):
        self.asset = asset
        self._transaction_list: list[Transaction] = []

        if transaction_list:
            for transaction in transaction_list:
                self.add_transaction(transaction)

    @property
    def asset(self) -> Asset:
        """Return the asset associated with the position.

        Returns:
            Asset: The asset instance.
        """
        return self._asset

    @property
    def transaction_list(self) -> list[Transaction]:
        """Return a copy of the transaction list.

        Returns:
            list[Transaction]: The list of transactions for this position.
        """
        return self._transaction_list.copy()

    @property
    def quantity(self) -> Decimal:
        """Return the net quantity held in the position.

        Returns:
            Decimal: The net quantity after buys and sells.
        """
        total = Decimal("0")
        for transaction in self._transaction_list:
            if transaction.transaction_type == TransactionType.BUY:
                total += transaction.quantity
            elif transaction.transaction_type == TransactionType.SELL:
                total -= transaction.quantity
            
        return total

    @asset.setter
    def asset(self,value: Asset) -> None:
        """Set the asset for the position.

        Args:
            value (Asset): The asset instance.

        Raises:
            InvalidValueError: If value is not an Asset.
        """
        if not isinstance(value, Asset):
            raise InvalidValueError("Asset deve ser uma instância de Asset")
        self._asset = value

    def add_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the position.

        Args:
            transaction (Transaction): The transaction to add.

        Raises:
            InvalidValueError: If transaction is not a Transaction or asset does
                not match the position asset.
            InsufficientBalanceError: If selling more than the available quantity.
        """
        if not isinstance(transaction, Transaction):
            raise InvalidValueError("transaction tem ser do tipo Transaction")
        
        if transaction.asset != self.asset:
            raise InvalidValueError("Ativo de transacao não pode ser diferente da posição")
        
        if transaction.transaction_type == TransactionType.SELL:
            if transaction.quantity > self.quantity:
                raise InsufficientBalanceError("Não é possivel vender mais do que possui")
        
        self._transaction_list.append(transaction)

    @property
    def average_price(self) -> Decimal:
        """Return the average purchase price for the position.

        Returns:
            Decimal: The weighted average price of all buy transactions.
        """
        current_quantity = Decimal("0")
        current_average_price = Decimal("0")

        sorted_transactions = sorted(self._transaction_list, key=lambda tx: tx.transaction_date)

        for transaction in sorted_transactions:
            if transaction.transaction_type == TransactionType.BUY:
                new_quantity = current_quantity + transaction.quantity
                total_value = (current_quantity * current_average_price) + (transaction.quantity * transaction.price)

                if new_quantity > 0:
                    current_average_price = total_value / new_quantity 
                else :
                    current_average_price = Decimal("0")

                current_quantity = new_quantity
            
            elif transaction.transaction_type == TransactionType.SELL:
                 current_quantity -= transaction.quantity

        return current_average_price