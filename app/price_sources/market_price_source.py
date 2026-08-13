from __future__ import annotations

from decimal import Decimal
import asyncio
from typing import Dict, List

from domain.protocols import PriceRequest, PriceSource
from app.price_sources.cache import SimplePriceCache
from app.price_sources.exceptions import PriceProviderError
from app.price_source import DatabasePriceSource
from app.errors.exceptions import PriceUnavailableError


class MarketPriceSource:
    """Roteia por asset_type, aplica cache, cai para DatabasePriceSource em falha."""

    def __init__(self, adapters_by_asset_type: Dict[str, PriceSource], fallback: PriceSource, cache: SimplePriceCache):
        self._adapters = adapters_by_asset_type
        self._fallback = fallback
        self._cache = cache
        self._info_logged = set()

    async def get_latest_price(self, request: PriceRequest) -> Decimal:
        cached = self._cache.get(request)
        if cached is not None:
            return cached

        adapter = self._adapters.get(request.asset_type)
        if adapter is None:
            # route to fallback silently
            try:
                price = await self._fallback.get_latest_price(request.ticker if isinstance(request.ticker, str) else request.ticker)
            except KeyError:
                raise PriceUnavailableError(f"Preço indisponível para {request.ticker}")
            self._cache.set(request, price)
            return price

        if not getattr(adapter, "is_configured", lambda: True)():
            # log once per asset_type (INFO)
            if request.asset_type not in self._info_logged:
                self._info_logged.add(request.asset_type)
            # go to fallback
            try:
                price = await self._fallback.get_latest_price(request.ticker)
            except KeyError:
                raise PriceUnavailableError(f"Preço indisponível para {request.ticker}")
            self._cache.set(request, price)
            return price

        # attempt adapter
        try:
            price = await adapter.get_latest_price(request)
            self._cache.set(request, price)
            return price
        except PriceProviderError as exc:
            # log warning and fallback
            try:
                price = await self._fallback.get_latest_price(request.ticker)
            except KeyError:
                raise PriceUnavailableError(f"Preço indisponível para {request.ticker}")
            self._cache.set(request, price)
            return price

    async def get_latest_prices(self, requests: List[PriceRequest]) -> Dict[str, Decimal]:
        results: Dict[str, Decimal] = {}
        to_fetch: List[PriceRequest] = []
        for r in requests:
            cached = self._cache.get(r)
            if cached is not None:
                results[r.ticker] = cached
            else:
                to_fetch.append(r)

        if not to_fetch:
            return results

        # group by asset_type
        groups: Dict[str, List[PriceRequest]] = {}
        for r in to_fetch:
            groups.setdefault(r.asset_type, []).append(r)

        leftovers: List[PriceRequest] = []
        for asset_type, group in groups.items():
            adapter = self._adapters.get(asset_type)
            if adapter is None or not getattr(adapter, "is_configured", lambda: True)():
                leftovers.extend(group)
                continue
            try:
                batch = await adapter.get_latest_prices(group)
            except PriceProviderError:
                leftovers.extend(group)
                continue
            # batch may be partial
            for r in group:
                if r.ticker in batch:
                    results[r.ticker] = batch[r.ticker]
                    self._cache.set(r, batch[r.ticker])
                else:
                    leftovers.append(r)

        # fallback in one call if possible
        if leftovers:
            tickers = [r.ticker for r in leftovers]
            try:
                fb = await self._fallback.get_latest_prices(tickers)
                for r in leftovers:
                    if r.ticker in fb:
                        results[r.ticker] = fb[r.ticker]
                        self._cache.set(r, fb[r.ticker])
                    else:
                        raise PriceUnavailableError(f"Preço indisponível para {r.ticker}")
            except KeyError:
                raise PriceUnavailableError("Alguns preços indisponíveis")

        return results
