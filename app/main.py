import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .config import settings
from .database import async_engine
from .routers import admin_router, asset_router, auth_router, portfolio_router, portfolio_v2_router
from .errors import register_exception_handlers
from .price_sources.brapi_source import BrapiPriceSource
from .price_sources.cache import QuoteCache
from .service.quote_service import QuoteService


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.PRICE_FETCH_TIMEOUT_SECONDS),
            limits=httpx.Limits(
                max_connections=settings.PRICE_HTTP_MAX_CONCURRENCY,
                max_keepalive_connections=settings.PRICE_HTTP_MAX_CONCURRENCY,
            ),
        ) as client:
            service = QuoteService(
                BrapiPriceSource(
                    client, settings.BRAPI_TOKEN,
                    batch_size=settings.PRICE_BATCH_SIZE,
                    max_concurrency=settings.PRICE_HTTP_MAX_CONCURRENCY,
                ),
                QuoteCache(settings.PRICE_CACHE_MAX_ENTRIES, settings.PRICE_CACHE_TTL_SECONDS),
            )
            app.state.quote_service = service
            try:
                yield
            finally:
                await service.aclose()
                del app.state.quote_service
    finally:
        await async_engine.dispose()


app = FastAPI(title="FinTrack API", lifespan=lifespan)


@app.get("/health/live", include_in_schema=False)
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
async def readiness():
    try:
        async with asyncio.timeout(settings.DATABASE_READY_TIMEOUT):
            async with async_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        # No driver error, hostname, credentials or external service details in HTTP/logs.
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router.router)
app.include_router(asset_router.router)
app.include_router(portfolio_router.router)
app.include_router(portfolio_v2_router.router)
app.include_router(admin_router.router)
