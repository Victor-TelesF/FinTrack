from __future__ import annotations

from decimal import Decimal
import asyncio
import logging
from typing import Dict, List

from domain.protocols import PriceRequest, PriceSource
from app.price_sources.cache import SimplePriceCache
from app.price_sources.exceptions import PriceProviderError
from app.price_source import DatabasePriceSource
from app.errors.exceptions import PriceUnavailableError

logger = logging.getLogger(__name__)


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

        async with self._cache.lock_for(request):
            cached = self._cache.get(request)
            if cached is not None:
                return cached

            adapter = self._adapters.get(request.asset_type)
            if adapter is None:
                try:
                    price = await self._fallback.get_latest_price(request)
                except KeyError:
                    raise PriceUnavailableError(f"Preço indisponível para {request.ticker}")
                self._cache.set(request, price)
                return price

            if not getattr(adapter, "is_configured", lambda: True)():
                if request.asset_type not in self._info_logged:
                    logger.info("Provider desabilitado para asset_type=%s; usando fallback para %s", request.asset_type, request.ticker)
                    self._info_logged.add(request.asset_type)
                try:
                    price = await self._fallback.get_latest_price(request)
                except KeyError:
                    raise PriceUnavailableError(f"Preço indisponível para {request.ticker}")
                self._cache.set(request, price)
                return price

            try:
                price = await adapter.get_latest_price(request)
                self._cache.set(request, price)
                return price
            except PriceProviderError as exc:
                logger.warning("Falha ao obter preço para %s (%s): %s", request.ticker, request.asset_type, exc)
                try:
                    price = await self._fallback.get_latest_price(request)
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

        groups: Dict[str, List[PriceRequest]] = {}
        for r in to_fetch:
            groups.setdefault(r.asset_type, []).append(r)

        leftovers: List[PriceRequest] = []
        for asset_type, group in groups.items():
            adapter = self._adapters.get(asset_type)
            if adapter is None:
                leftovers.extend(group)
                continue
            if not getattr(adapter, "is_configured", lambda: True)():
                if asset_type not in self._info_logged:
                    logger.info("Provider desabilitado para asset_type=%s; usando fallback para %s", asset_type, [r.ticker for r in group])
                    self._info_logged.add(asset_type)
                leftovers.extend(group)
                continue
            try:
                batch = await adapter.get_latest_prices(group)
            except PriceProviderError as exc:
                logger.warning("Falha ao obter lote para asset_type=%s: %s", asset_type, exc)
                leftovers.extend(group)
                continue
            for r in group:
                async with self._cache.lock_for(r):
                    cached = self._cache.get(r)
                    if cached is not None:
                        results[r.ticker] = cached
                        continue
                    if r.ticker in batch:
                        results[r.ticker] = batch[r.ticker]
                        self._cache.set(r, batch[r.ticker])
                    else:
                        leftovers.append(r)

        failed_tickers: List[str] = []
        if leftovers:
            tickers = [r.ticker for r in leftovers]
            try:
                fb = await self._fallback.get_latest_prices(leftovers)
                for r in leftovers:
                    async with self._cache.lock_for(r):
                        cached = self._cache.get(r)
                        if cached is not None:
                            results[r.ticker] = cached
                            continue
                        if r.ticker in fb:
                            results[r.ticker] = fb[r.ticker]
                            self._cache.set(r, fb[r.ticker])
                        else:
                            failed_tickers.append(r.ticker)
            except KeyError:
                failed_tickers.extend(tickers)

        if failed_tickers:
            raise PriceUnavailableError(f"Preços indisponíveis para: {', '.join(failed_tickers)}")

        return results
