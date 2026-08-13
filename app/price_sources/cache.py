from __future__ import annotations

import asyncio
import time
from typing import Tuple
from domain.protocols import PriceRequest


class _CacheEntry:
    def __init__(self, value, ts: float):
        self.value = value
        self.ts = ts


class SimplePriceCache:
    """In-memory TTL cache. Not shared between replicas.

    Key is (ticker, asset_type, external_price_id).
    """

    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._store: dict[Tuple[str, str, str | None], _CacheEntry] = {}
        self._locks: dict[Tuple[str, str, str | None], asyncio.Lock] = {}

    def _key(self, request: PriceRequest):
        return (request.ticker, request.asset_type, request.external_price_id)

    def get(self, request: PriceRequest):
        key = self._key(request)
        entry = self._store.get(key)
        if entry and (time.time() - entry.ts) < self._ttl:
            return entry.value
        return None

    def set(self, request: PriceRequest, value):
        key = self._key(request)
        self._store[key] = _CacheEntry(value, time.time())

    def lock_for(self, request: PriceRequest) -> asyncio.Lock:
        key = self._key(request)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock
