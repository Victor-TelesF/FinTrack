from enum import Enum

class LiquidityType(Enum):
    DIARIA = "diaria"
    NO_VENCIMENTO = "no_vencimento"
    PERIODICA = "periodica"

class IndexType(Enum):
    CDI = "cdi"
    IPCA = "ipca"
    PREFIXADO = "prefixado"

class BondIndexType(Enum):
    SELIC = "selic"
    IPCA = "ipca"
    PREFIXADO = "prefixado"

class Currency(Enum):
    BRL = "brl"
    USD = "usd"
    EUR = "eur"

class TransactionType(Enum):
    BUY = "buy"
    SELL = "sell"