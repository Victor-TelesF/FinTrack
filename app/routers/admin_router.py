from fastapi import APIRouter, Depends, Header

from app.config import settings
from app.dependencies import get_asset_service
from app.errors.exceptions import InvalidAdminKeyError
from app.schemas.asset_schema import AdminAssetUpsertRequest
from app.service.asset_service import AssetService

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_KEY or x_admin_key != settings.ADMIN_KEY:
        raise InvalidAdminKeyError()


@router.post("/assets")
def upsert_assets(
    payload: AdminAssetUpsertRequest,
    service: AssetService = Depends(get_asset_service),
    _: None = Depends(verify_admin_key),
):
    return service.upsert_many(payload.assets)