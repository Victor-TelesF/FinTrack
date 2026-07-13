from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class MarketRates:
    cdi_rate: Decimal | None = None
    ipca_rate: Decimal | None = None
    selic_rate: Decimal | None = None

@dataclass(slots=True)
class ReturnContext:
    purchase_price: Decimal | None = None
    dividends_received: Decimal | None = None
    market_rates: MarketRates | None = None