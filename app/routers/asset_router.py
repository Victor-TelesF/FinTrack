from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_asset_service, get_current_user, get_quote_service
from app.models import UserModel
from app.schemas.asset_schema import AssetQuoteCatalogRead, MarketAssetRead, MarketAssetSearchRead
from app.service.asset_service import AssetService
from app.service.quote_service import QuoteService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/search", response_model=MarketAssetSearchRead)
async def search_market_assets(
    q: str = Query(..., min_length=1, max_length=50, description="Texto para busca do mercado"),
    asset_type: Literal["national_stock", "real_estate_fund"] = Query(..., alias="type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    quotes: QuoteService = Depends(get_quote_service),
    _: UserModel = Depends(get_current_user),
):
    try:
        return await quotes.search_market(q.strip(), asset_type, page=page, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/market/{ticker}", response_model=MarketAssetRead)
async def get_market_asset(
    ticker: str,
    asset_type: Literal["national_stock", "real_estate_fund"] | None = Query(
        None, alias="type",
    ),
    quotes: QuoteService = Depends(get_quote_service),
    _: UserModel = Depends(get_current_user),
):
    normalized = ticker.strip().upper()
    if not normalized:
        raise HTTPException(status_code=422, detail="Ticker de mercado inválido")
    try:
        asset = await quotes.resolve_market(normalized, asset_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if asset is None:
        raise HTTPException(status_code=404, detail="Ativo de mercado não encontrado")
    return asset


@router.get("", response_model=list[AssetQuoteCatalogRead])
async def list_assets(
    service: AssetService = Depends(get_asset_service),
    _: UserModel = Depends(get_current_user),
):
    return await service.list()


@router.get("/{asset_id}", response_model=AssetQuoteCatalogRead)
async def get_asset(
    asset_id: UUID,
    service: AssetService = Depends(get_asset_service),
    _: UserModel = Depends(get_current_user),
):
    return await service.get(asset_id)
