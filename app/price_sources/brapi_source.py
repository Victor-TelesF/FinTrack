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

from .types import MarketQuote, PriceKey, QuoteFailure, QuoteResult


class BrapiPriceSource:
    URL = "https://brapi.dev/api/v2/stocks/quote"

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
