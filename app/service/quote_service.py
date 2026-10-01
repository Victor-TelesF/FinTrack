import asyncio
import re
from collections.abc import Sequence
from dataclasses import asdict
from uuid import UUID

from app.price_sources.cache import QuoteCache
from app.price_sources.exceptions import QuoteConfigurationError, QuoteUnavailableError
from app.price_sources.types import (
    AsyncPriceSource, MarketQuote, PriceKey, PriceRequest, Quote, QuoteFailure, QuoteResult,
)


class QuoteService:
    """Process-local market quotes. No ORM sessions or transaction prices here."""

    def __init__(self, source: AsyncPriceSource, cache: QuoteCache):
        self._source = source
        self._cache = cache
        self._inflight: dict[PriceKey, asyncio.Task[dict[PriceKey, QuoteResult]]] = {}
        self._closed = False

    async def get_quotes(self, requests: Sequence[PriceRequest]) -> dict[UUID, Quote]:
        if self._closed:
            raise RuntimeError("Quote service is closed")
        invalid = [
            request.asset_id for request in requests
            if request.source != "brapi" or request.currency != "BRL"
            or not re.fullmatch(r"[A-Z0-9]+", request.external_price_id)
        ]
        identities = {}
        for request in requests:
            if request.asset_id in identities and identities[request.asset_id] != request.key:
                invalid.append(request.asset_id)
            identities[request.asset_id] = request.key
        if invalid:
            raise QuoteConfigurationError(list(dict.fromkeys(invalid)))

        cached = {}
        pending = {}
        missing = []
        for key in dict.fromkeys(request.key for request in requests):
            quote = self._cache.get(key)
            if quote is not None:
                cached[key] = quote
            elif key in self._inflight:
                pending[key] = self._inflight[key]
            else:
                missing.append(key)

        # No await between checking and registering: concurrent callers share the tasks.
        for i in range(0, len(missing), self._source.batch_size):
            batch = missing[i:i + self._source.batch_size]
            task = asyncio.create_task(self._fetch_and_cache(batch))
            for key in batch:
                self._inflight[key] = task
                pending[key] = task
            task.add_done_callback(lambda done, keys=tuple(batch): self._release(done, keys))

        fetched = {}
        for task in dict.fromkeys(pending.values()):
            # One disconnected caller must not cancel a fetch shared by other callers.
            fetched.update(await asyncio.shield(task))
        quotes = {}
        failures = {}
        for request in requests:
            result = cached.get(request.key) or fetched.get(request.key, QuoteFailure("missing_quote"))
            if isinstance(result, QuoteFailure):
                failures[request.asset_id] = result
            else:
                quotes[request.asset_id] = Quote(
                    **asdict(result), asset_id=request.asset_id, from_cache=request.key in cached,
                )
        if failures:
            raise QuoteUnavailableError(failures)
        return quotes

    async def _fetch_and_cache(self, keys: Sequence[PriceKey]) -> dict[PriceKey, QuoteResult]:
        results = await self._source.fetch_many(keys)
        for key in keys:
            result = results.get(key)
            if isinstance(result, MarketQuote):
                self._cache.put(key, result)
        return results

    def _release(self, task: asyncio.Task, keys: Sequence[PriceKey]) -> None:
        for key in keys:
            if self._inflight.get(key) is task:
                del self._inflight[key]
        if not task.cancelled():
            # Retrieve background exceptions even when all requesters disconnected.
            task.exception()

    async def aclose(self) -> None:
        self._closed = True
        tasks = set(self._inflight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._inflight.clear()
