import secrets

from fastapi import APIRouter, Depends, Header

from app.config import settings
from app.dependencies import get_asset_service
from app.errors.exceptions import InvalidAdminKeyError
from app.schemas.asset_schema import AssetCatalogRead, AdminAssetUpsertRequest
from app.service.asset_service import AssetService

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_KEY or not secrets.compare_digest(x_admin_key or "", settings.ADMIN_KEY):
        raise InvalidAdminKeyError()


@router.post("/assets", response_model=list[AssetCatalogRead])
def upsert_assets(
    payload: AdminAssetUpsertRequest,
    service: AssetService = Depends(get_asset_service),
    _: None = Depends(verify_admin_key),
):
    return service.upsert_many(payload.assets)