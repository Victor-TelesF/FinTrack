"""Define shared enumerations used across the domain.

This module exposes liquidity, indexing, currency, and transaction type
enumerations for asset and portfolio logic.
"""

from enum import Enum

class LiquidityType(Enum):
    """Liquidity classifications for fixed income assets."""
    DIARIA = "diaria"
    NO_VENCIMENTO = "no_vencimento"
    PERIODICA = "periodica"

class IndexType(Enum):
    """Index types for fixed income assets."""
    CDI = "cdi"
    IPCA = "ipca"
    PREFIXADO = "prefixado"

class BondIndexType(Enum):
    """Index types specific to government bonds."""
    SELIC = "selic"
    IPCA = "ipca"
    PREFIXADO = "prefixado"

class Currency(Enum):
    """Supported currencies for variable income assets."""
    BRL = "brl"
    USD = "usd"
    EUR = "eur"

class TransactionType(Enum):
    """Transaction actions for portfolio trading."""
    BUY = "buy"
    SELL = "sell"