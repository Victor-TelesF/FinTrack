from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PriceKey:
    source: str
    external_price_id: str
    currency: str


@dataclass(frozen=True)
class PriceRequest:
    asset_id: UUID
    source: str
    external_price_id: str
    currency: str

    @property
    def key(self) -> PriceKey:
        return PriceKey(self.source, self.external_price_id, self.currency)


@dataclass(frozen=True)
class MarketQuote:
    price: Decimal
    currency: str
    source: str
    quoted_at: datetime | None
    fetched_at: datetime


@dataclass(frozen=True)
class Quote(MarketQuote):
    asset_id: UUID
    from_cache: bool = False


@dataclass(frozen=True)
class QuoteFailure:
    # Safe internal codes only; never store provider bodies, headers or exceptions.
    code: str
    retry_after_seconds: float | None = None


type QuoteResult = MarketQuote | QuoteFailure


@dataclass(frozen=True)
class MarketAsset:
    ticker: str
    name: str
    asset_type: str
    quote_currency: str
    quote: MarketQuote | None = None


@dataclass(frozen=True)
class MarketAssetSearchResult:
    items: list[MarketAsset]
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next_page: bool = False


@dataclass(frozen=True)
class MarketProviderCapability:
    provider: str
    supported_asset_types: tuple[str, ...]
    quote_currency: str = "BRL"


class AsyncPriceSource(Protocol):
    batch_size: int

    async def fetch_many(self, keys: Sequence[PriceKey]) -> dict[PriceKey, QuoteResult]: ...
