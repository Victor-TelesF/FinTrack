from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.errors.exceptions import AssetAlreadyExistsError
from app.mappers.asset_mapper import AssetMapper
from app.models import AssetModel
from app.schemas.asset_schema import AdminAssetItem, AssetCatalogRead
from app.schemas.fixed_income_schema import CDBCreate
from app.service.asset_service import AssetService

pytestmark = pytest.mark.asyncio


async def test_loaded_subclass_fields_support_mapping_after_session_close(
    async_session_factory, legacy_http_examples
):
    items = [
        AdminAssetItem.model_validate(item)
        for item in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]
    ]
    async with async_session_factory() as session:
        await AssetService(session).upsert_many(items)

    async with async_session_factory() as session:
        models = await AssetService(session).list()

    assert len(models) == 6
    for model in models:
        assert AssetCatalogRead.model_validate(model).ticker == model.ticker
        assert AssetMapper.to_domain(model).current_price == model.current_price


async def test_create_fixed_income_loads_persisted_values(async_db, legacy_http_examples):
    payload = next(
        item for item in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]
        if item["type"] == "cdb"
    )
    model = await AssetService(async_db).create(CDBCreate.model_validate(payload))
    async_db.expunge_all()

    response = AssetCatalogRead.model_validate(model)
    assert response.current_price == Decimal("100.00")
    assert response.rate == Decimal("0.12")
    assert response.fgc_covered is True


async def test_failed_batch_commit_rolls_back_insert_and_update(
    async_db, async_session_factory, monkeypatch
):
    service = AssetService(async_db)
    original = AdminAssetItem(
        type="national_stock", name="Original", ticker="EXIST3", current_price=Decimal("10")
    )
    await service.upsert_many([original])

    async def fail_after_flush():
        await async_db.flush()
        raise IntegrityError("synthetic batch failure", params={}, orig=Exception("constraint"))

    commit = AsyncMock(side_effect=fail_after_flush)
    monkeypatch.setattr(async_db, "commit", commit)
    with pytest.raises(AssetAlreadyExistsError):
        await service.upsert_many([
            original.model_copy(update={"name": "Updated", "current_price": Decimal("20")}),
            AdminAssetItem(type="national_stock", name="New", ticker="NEW3", current_price=Decimal("30")),
        ])

    commit.assert_awaited_once()
    assert not async_db.in_transaction()
    async with async_session_factory() as verification_session:
        models = list((await verification_session.scalars(select(AssetModel))).all())
        assert len(models) == 1
        assert models[0].name == "Original"
        assert models[0].current_price == Decimal("10")
