import asyncio
import json
import math
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from time import monotonic

import httpx
from pydantic import SecretStr

from .types import (
    MarketAsset, MarketAssetSearchResult, MarketProviderCapability, MarketQuote,
    PriceKey, QuoteFailure, QuoteResult,
)


class BrapiPriceSource:
    URL = "https://brapi.dev/api/v2/stocks/quote"
    MARKET_URL = "https://brapi.dev/api/v2/tickers"
    SUPPORTED_ASSET_TYPES = ("national_stock", "real_estate_fund")
    MARKET_TYPE_MAP = {
        "national_stock": ("stock", "stock"),
        "real_estate_fund": ("fund", "fii"),
    }

    def __init__(
        self, client: httpx.AsyncClient, token: SecretStr, *, batch_size: int = 1,
        max_concurrency: int = 1, clock: Callable[[], float] = monotonic,
    ):
        if batch_size < 1 or max_concurrency < 1:
            raise ValueError("Batch size and concurrency must be positive")
        self.batch_size = batch_size
        self._client = client
        self._token = token
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._clock = clock
        self._blocked_until = 0.0

    @classmethod
    def supported_asset_types(cls) -> tuple[str, ...]:
        return cls.SUPPORTED_ASSET_TYPES

    def get_capabilities(self) -> MarketProviderCapability:
        return MarketProviderCapability(
            provider="brapi",
            supported_asset_types=self.SUPPORTED_ASSET_TYPES,
            quote_currency="BRL",
        )

    @property
    def capabilities(self) -> MarketProviderCapability:
        return self.get_capabilities()

    @classmethod
    def normalize_market_type(cls, asset_type: str) -> tuple[str, str] | None:
        if asset_type is None:
            return None
        normalized = str(asset_type).strip().lower()
        return cls.MARKET_TYPE_MAP.get(normalized)

    async def fetch_many(self, keys: Sequence[PriceKey]) -> dict[PriceKey, QuoteResult]:
        unique = list(dict.fromkeys(keys))
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(self._fetch_batch(unique[i:i + self.batch_size]))
                for i in range(0, len(unique), self.batch_size)
            ]
        return {key: value for task in tasks for key, value in task.result().items()}

    async def _fetch_batch(self, keys: Sequence[PriceKey]) -> dict[PriceKey, QuoteResult]:
        token = self._token.get_secret_value().strip()
        if not token:
            return self._failed(keys, "missing_token")
        async with self._semaphore:
            remaining = self._blocked_until - self._clock()
            if remaining > 0:
                return self._failed(keys, "rate_limited", remaining)
            try:
                response = await self._client.get(
                    self.URL,
                    params={"symbols": ",".join(key.external_price_id for key in keys)},
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                )
            except httpx.TimeoutException:
                return self._failed(keys, "timeout")
            except httpx.RequestError:
                return self._failed(keys, "network_error")

            if response.status_code == 429:
                delay = self._retry_after(response.headers.get("Retry-After"))
                self._blocked_until = max(self._blocked_until, self._clock() + delay)
                return self._failed(keys, "rate_limited", delay)
            if response.status_code != 200:
                code = {
                    400: "invalid_request", 401: "authentication_error",
                    403: "access_denied", 404: "missing_quote",
                }.get(response.status_code, "provider_unavailable" if response.status_code >= 500 else "invalid_response")
                return self._failed(keys, code)
            fetched_at = datetime.now(timezone.utc)
            try:
                # Parse directly to Decimal; never round through a binary float.
                body = json.loads(response.content, parse_float=Decimal)
            except (ValueError, UnicodeDecodeError):
                return self._failed(keys, "invalid_response")
            if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                return self._failed(keys, "invalid_response")
            rows: dict[str, list[dict]] = {}
            for item in body["results"]:
                if not isinstance(item, dict) or not isinstance(item.get("requestedSymbol"), str):
                    return self._failed(keys, "invalid_response")
                rows.setdefault(item["requestedSymbol"], []).append(item)
            results = {}
            for key in keys:
                matches = rows.get(key.external_price_id, [])
                if not matches:
                    results[key] = QuoteFailure("missing_quote")
                elif len(matches) != 1:
                    results[key] = QuoteFailure("invalid_response")
                else:
                    results[key] = self._normalize(matches[0], key, fetched_at)
            return results

    @staticmethod
    def _normalize(item: dict, key: PriceKey, fetched_at: datetime) -> QuoteResult:
        # Renames may involve conversion ratios: require an explicit mapping review.
        if item.get("changed") is not False or item.get("symbol") != key.external_price_id:
            return QuoteFailure("identity_mismatch")
        data = item.get("data")
        if not isinstance(data, dict):
            return QuoteFailure("invalid_response")
        if data.get("currency") != key.currency:
            return QuoteFailure("currency_mismatch")
        value = data.get("regularMarketPrice")
        if isinstance(value, bool) or not isinstance(value, (int, Decimal, str)):
            return QuoteFailure("invalid_price")
        try:
            price = Decimal(value)
        except InvalidOperation:
            return QuoteFailure("invalid_price")
        if not price.is_finite() or price <= 0:
            return QuoteFailure("invalid_price")
        quoted_at = data.get("regularMarketTime")
        if quoted_at is not None:
            if not isinstance(quoted_at, str):
                return QuoteFailure("invalid_timestamp")
            try:
                quoted_at = datetime.fromisoformat(quoted_at)
            except ValueError:
                return QuoteFailure("invalid_timestamp")
            if quoted_at.tzinfo is None:
                return QuoteFailure("invalid_timestamp")
            quoted_at = quoted_at.astimezone(timezone.utc)
        return MarketQuote(price, key.currency, "brapi", quoted_at, fetched_at)

    async def search_market(
        self,
        query: str,
        asset_type: str,
        page: int = 1,
        limit: int = 20,
    ) -> MarketAssetSearchResult:
        market_type = self.normalize_market_type(asset_type)
        if market_type is None:
            raise ValueError(f"Unsupported market asset type: {asset_type!r}")
        if page < 1 or limit < 1 or limit > 100:
            raise ValueError("Market page and limit must be positive and within provider limits")
        search = (query or "").strip()
        if not search or len(search) > 50:
            raise ValueError("Market search query must be 1-50 non-empty characters")
        token = self._token.get_secret_value().strip()
        if not token:
            return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
        async with self._semaphore:
            remaining = self._blocked_until - self._clock()
            if remaining > 0:
                return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
            try:
                response = await self._client.get(
                    self.MARKET_URL,
                    params={
                        "search": search,
                        "type": market_type[0],
                        "subType": market_type[1],
                        "page": page,
                        "limit": limit,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                )
            except httpx.TimeoutException:
                return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
            except httpx.RequestError:
                return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)

        if response.status_code == 429:
            delay = self._retry_after(response.headers.get("Retry-After"))
            self._blocked_until = max(self._blocked_until, self._clock() + delay)
            return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
        if response.status_code not in {200}:
            return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
        try:
            body = json.loads(response.content, parse_float=Decimal)
        except (ValueError, UnicodeDecodeError):
            return MarketAssetSearchResult(items=[], page=page, limit=limit, total_items=0, total_pages=0, has_next_page=False)
        items = self._coerce_market_items(body)
        total_items = self._extract_total_items(body, items)
        total_pages = 0 if total_items == 0 else max(1, (total_items + limit - 1) // limit)
        has_next_page = bool(total_pages and page < total_pages)
        return MarketAssetSearchResult(
            items=items,
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next_page=has_next_page,
        )

    async def search(self, query: str, asset_type: str, page: int = 1, limit: int = 20):
        return await self.search_market(query, asset_type, page=page, limit=limit)

    async def resolve_market(self, ticker: str, asset_type: str | None = None) -> MarketAsset | None:
        if not ticker or not str(ticker).strip():
            return None
        normalized_ticker = str(ticker).strip().upper()
        asset_type_key = asset_type or "national_stock"
        type_pair = self.normalize_market_type(asset_type_key)
        if type_pair is None:
            raise ValueError(f"Unsupported market asset type: {asset_type_key!r}")
        token = self._token.get_secret_value().strip()
        if not token:
            return None
        async with self._semaphore:
            remaining = self._blocked_until - self._clock()
            if remaining > 0:
                return None
            try:
                response = await self._client.get(
                    self.MARKET_URL,
                    params={
                        "search": normalized_ticker,
                        "type": type_pair[0],
                        "subType": type_pair[1],
                        "page": 1,
                        "limit": 100,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                )
            except httpx.TimeoutException:
                return None
            except httpx.RequestError:
                return None

        if response.status_code == 429:
            delay = self._retry_after(response.headers.get("Retry-After"))
            self._blocked_until = max(self._blocked_until, self._clock() + delay)
            return None
        if response.status_code != 200:
            return None
        try:
            body = json.loads(response.content, parse_float=Decimal)
        except (ValueError, UnicodeDecodeError):
            return None
        matches = self._coerce_market_items(body)
        exact = [item for item in matches if item.ticker == normalized_ticker]
        if not exact:
            return None
        return exact[0]

    async def resolve(self, ticker: str, asset_type: str | None = None):
        return await self.resolve_market(ticker, asset_type)

    async def search_market_assets(self, query: str, asset_type: str, page: int = 1, limit: int = 20):
        return await self.search_market(query, asset_type, page=page, limit=limit)

    async def resolve_market_asset(self, ticker: str, asset_type: str | None = None):
        return await self.resolve_market(ticker, asset_type)

    @staticmethod
    def _coerce_market_items(body: object) -> list[MarketAsset]:
        if not isinstance(body, dict):
            return []
        rows = body.get("results")
        if rows is None:
            rows = body.get("items") or body.get("stocks") or []
        if not isinstance(rows, list):
            return []
        fetched_at = datetime.now(timezone.utc)
        assets: list[MarketAsset] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = row.get("symbol") or row.get("ticker") or row.get("stock")
            name = row.get("name") or symbol or ""
            if not isinstance(symbol, str) or not symbol.strip():
                continue
            market_type = row.get("assetType") or row.get("type")
            subtype = row.get("subType") or row.get("subtype") or ""
            asset_type = BrapiPriceSource._classify_market_asset(market_type, subtype)
            if asset_type is None:
                continue
            quote_currency = row.get("currency") or row.get("quoteCurrency") or "BRL"
            price = row.get("regularMarketPrice")
            quote = None
            if isinstance(price, (int, str, Decimal)) and not isinstance(price, bool):
                try:
                    price_value = Decimal(price)
                except InvalidOperation:
                    price_value = None
                if price_value is not None and price_value.is_finite() and price_value > 0:
                    quoted_at_raw = row.get("regularMarketTime")
                    quoted_at = None
                    if isinstance(quoted_at_raw, str):
                        try:
                            quoted_at = datetime.fromisoformat(quoted_at_raw)
                        except ValueError:
                            quoted_at = None
                        if quoted_at is not None and quoted_at.tzinfo is None:
                            quoted_at = None
                        if quoted_at is not None:
                            quoted_at = quoted_at.astimezone(timezone.utc)
                    quote = MarketQuote(price_value, str(quote_currency).upper(), "brapi", quoted_at, fetched_at)
            assets.append(MarketAsset(
                ticker=str(symbol).strip().upper(),
                name=str(name).strip() or str(symbol).strip().upper(),
                asset_type=asset_type,
                quote_currency=str(quote_currency).upper(),
                quote=quote,
            ))
        return assets

    @staticmethod
    def _extract_total_items(body: object, items: list[MarketAsset]) -> int:
        if not isinstance(body, dict):
            return len(items)
        total = body.get("total")
        if isinstance(total, int) and total >= 0:
            return total
        total_pages = body.get("totalPages")
        if isinstance(total_pages, int) and total_pages >= 0:
            page = body.get("page")
            limit = body.get("limit")
            if isinstance(page, int) and page >= 1 and isinstance(limit, int) and limit > 0:
                return total_pages * limit
        return len(items)

    @staticmethod
    def _classify_market_asset(asset_type: object, subtype: object) -> str | None:
        asset_name = str(asset_type).strip().lower() if isinstance(asset_type, str) else ""
        subtype_name = str(subtype).strip().lower() if isinstance(subtype, str) else ""
        if asset_name == "stock" and subtype_name == "stock":
            return "national_stock"
        if asset_name == "fund" and subtype_name == "fii":
            return "real_estate_fund"
        return None

    @staticmethod
    def _failed(keys: Sequence[PriceKey], code: str, retry_after: float | None = None):
        return {key: QuoteFailure(code, retry_after) for key in keys}

    @staticmethod
    def _retry_after(value: str | None) -> float:
        if value is not None:
            try:
                seconds = float(value)
                if math.isfinite(seconds) and seconds >= 0:
                    return seconds
            except ValueError:
                try:
                    deadline = parsedate_to_datetime(value)
                    if deadline.tzinfo is not None:
                        return max(0, (deadline - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
        return 60.0
