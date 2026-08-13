from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_asset_service, get_current_user
from app.models import UserModel
from app.schemas.asset_schema import AssetCatalogRead
from app.service.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetCatalogRead])
async def list_assets(
    service: AssetService = Depends(get_asset_service),
    _: UserModel = Depends(get_current_user),
):
    return await service.list()


@router.get("/{asset_id}", response_model=AssetCatalogRead)
async def get_asset(
    asset_id: UUID,
    service: AssetService = Depends(get_asset_service),
    _: UserModel = Depends(get_current_user),
):
    return await service.get(asset_id)