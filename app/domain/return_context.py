"""Define return context structures for calculations.

This module contains dataclasses used to encapsulate market rates and return
calculation context values.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class MarketRates:
    """Market rate values used in return calculations."""

    cdi_rate: Decimal | None = None
    ipca_rate: Decimal | None = None
    selic_rate: Decimal | None = None


@dataclass(slots=True)
class ReturnContext:
    """Context values used when calculating asset returns."""

    purchase_price: Decimal | None = None
    dividends_received: Decimal | None = None
    market_rates: MarketRates | None = None