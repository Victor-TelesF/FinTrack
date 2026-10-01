"""Controlled backend-only smoke check: uv run --locked python -m scripts.check_brapi."""
import asyncio
import json
from uuid import uuid4

from app.config import settings
from app.main import app, lifespan
from app.price_sources.exceptions import QuoteUnavailableError
from app.price_sources.types import PriceRequest


async def main() -> int:
    if not settings.BRAPI_TOKEN.get_secret_value().strip():
        print("BRAPI_TOKEN ausente. Configure no .env local ou no ambiente do backend.")
        return 1
    # One equity outside the public stock sandbox also verifies authentication.
    requests = [PriceRequest(uuid4(), "brapi", symbol, "BRL") for symbol in ("BBDC4", "HGLG11")]
    async with lifespan(app):
        service = app.state.quote_service
        failed = False
        for request in requests:
            try:
                quote = (await service.get_quotes([request]))[request.asset_id]
                cached = (await service.get_quotes([request]))[request.asset_id]
                print(json.dumps({
                    "symbol": request.external_price_id, "price": str(quote.price),
                    "currency": quote.currency, "source": quote.source,
                    "quoted_at": quote.quoted_at.isoformat() if quote.quoted_at else None,
                    "fetched_at": quote.fetched_at.isoformat(), "second_read_from_cache": cached.from_cache,
                }))
            except QuoteUnavailableError as exc:
                failed = True
                print(json.dumps({"symbol": request.external_price_id,
                                  "error": exc.failures[request.asset_id].code}))
        return int(failed)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
