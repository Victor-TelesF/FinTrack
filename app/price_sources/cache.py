from collections import OrderedDict
from collections.abc import Callable
from time import monotonic

from .types import MarketQuote, PriceKey


class QuoteCache:
    """Bounded LRU cache. TTL measures retrieval age, not market quote age."""

    def __init__(self, max_entries: int, ttl_seconds: float, clock: Callable[[], float] = monotonic):
        if max_entries <= 0 or ttl_seconds <= 0:
            raise ValueError("Cache size and TTL must be positive")
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[PriceKey, tuple[float, MarketQuote]] = OrderedDict()

    def get(self, key: PriceKey) -> MarketQuote | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, quote = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return quote

    def put(self, key: PriceKey, quote: MarketQuote) -> None:
        self._entries[key] = (self._clock() + self._ttl, quote)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
