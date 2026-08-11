"""Define portfolio transaction records.

This module contains the Transaction entity used for recording asset purchases
and sales along with validation rules for quantity, price, type, and date.
"""

from decimal import Decimal
from ..enums import TransactionType
from ..assets import Asset
from ..reference_date import reference_date
from datetime import date
from uuid import uuid4
from ..exceptions import InvalidQuantityError, InvalidPriceError, InvalidTransactionTypeError, InvalidTransactionDateError, InvalidValueError


class Transaction:
    """Represents a portfolio transaction.

    Args:
        asset (Asset): The asset involved in the transaction.
        quantity (Decimal): The quantity of the asset transacted.
        price (Decimal): The transaction price per asset unit.
        transaction_type (TransactionType): The transaction type.
        transaction_date (date): The transaction date.
    """

    def __init__(self, asset: Asset, quantity: Decimal,
                price: Decimal, transaction_type: TransactionType,
                transaction_date: date, transaction_sequence: int | None = None):
        self._id_transaction = uuid4()
        self.asset = asset
        self.quantity = quantity
        self.price = price
        self.transaction_type = transaction_type
        self.transaction_date = transaction_date
        self.transaction_sequence = transaction_sequence

    @property
    def id_transaction(self):
        """Return the transaction unique identifier.

        Returns:
            UUID: The transaction identifier.
        """
        return self._id_transaction

    @property
    def asset(self) -> Asset:
        """Return the asset associated with the transaction.

        Returns:
            Asset: The asset instance.
        """
        return self._asset
    
    @property
    def quantity(self) -> Decimal:
        """Return the quantity of the transaction.

        Returns:
            Decimal: The quantity of asset units transacted.
        """
        return self._quantity
    
    @property
    def price(self) -> Decimal:
        """Return the transaction price per unit.

        Returns:
            Decimal: The transaction price.
        """
        return self._price
    
    @property
    def transaction_type(self) -> TransactionType:
        """Return the transaction type.

        Returns:
            TransactionType: The transaction type.
        """
        return self._transaction_type
    
    @property
    def transaction_date(self) -> date:
        """Return the transaction date.

        Returns:
            date: The date of the transaction.
        """
        return self._transaction_date

    @property
    def transaction_sequence(self) -> int | None:
        return self._transaction_sequence

    @transaction_sequence.setter
    def transaction_sequence(self, value: int | None) -> None:
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise InvalidValueError("Sequência da transação deve ser um inteiro positivo")
        self._transaction_sequence = value
    
    @asset.setter
    def asset(self, value) -> None:
        """Set the transaction asset.

        Args:
            value (Asset): The asset instance.

        Raises:
            InvalidValueError: If value is not an Asset.
        """
        if not isinstance(value, Asset):
            raise InvalidValueError("Asset deve ser uma instância de Asset")
        self._asset = value
    
    @quantity.setter
    def quantity(self, quantity: Decimal) -> None:
        """Set the transaction quantity.

        Args:
            quantity (Decimal): The quantity to set.

        Raises:
            InvalidQuantityError: If quantity is not Decimal or is less than or
                equal to zero.
        """
        if not isinstance(quantity, Decimal):
            raise InvalidQuantityError("Quantidade da transação tem que ser Decimal, não float")

        if quantity <= 0:
            raise InvalidQuantityError("Quantidade da transação não pode ser zero ou negativo")
        
        self._quantity = quantity

    @price.setter
    def price(self, price: Decimal) -> None:
        """Set the transaction price.

        Args:
            price (Decimal): The price to set.

        Raises:
            InvalidPriceError: If price is not Decimal or is less than or equal
                to zero.
        """
        if not isinstance(price, Decimal):
            raise InvalidPriceError("Preço da transação tem que ser Decimal")
        
        if price <= 0:
            raise InvalidPriceError("Preço da transação não pode ser menor ou igual a zero")
        
        self._price = price

    @transaction_type.setter
    def transaction_type(self, value: TransactionType) -> None:
        """Set the transaction type.

        Args:
            value (TransactionType): The transaction type to set.

        Raises:
            InvalidTransactionTypeError: If value is not a TransactionType.
        """
        if not isinstance(value, TransactionType):
            raise InvalidTransactionTypeError("Tipo de transação invalida")
        
        self._transaction_type = value

    @transaction_date.setter
    def transaction_date(self, value: date) -> None:
        """Set the transaction date.

        Args:
            value (date): The transaction date.

        Raises:
            InvalidTransactionDateError: If value is not a date or is in the
                future.
        """
        if not isinstance(value, date):
            raise InvalidTransactionDateError("Data de transação tem que ser do tipo date")
        if value > reference_date():
            raise InvalidTransactionDateError("Data de transação não pode ser maior que hoje")
    
        self._transaction_date = value