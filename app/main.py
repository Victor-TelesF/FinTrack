from fastapi import FastAPI
from contextlib import asynccontextmanager
import httpx
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import admin_router, asset_router, auth_router, portfolio_router
from .errors import register_exception_handlers
from app.price_sources.cache import SimplePriceCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=settings.PRICE_FETCH_TIMEOUT_SECONDS)
    app.state.price_cache = SimplePriceCache(settings.PRICE_CACHE_TTL_SECONDS)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(title="FinTrack API", lifespan=lifespan)

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
app.include_router(admin_router.router)