import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.errors.exceptions import AssetAlreadyExistsError, InvalidAssetQuoteMetadataError
from app.mappers.asset_mapper import AssetMapper
from app.models import AssetModel
from app.models.variable_income_model import NationalStockModel
from app.schemas.asset_schema import AdminAssetItem, AssetCatalogRead
from app.schemas.fixed_income_schema import CDBCreate
from app.schemas.variable_income_schema import (
    CryptocurrencyCreate,
    NationalStockCreate,
    RealEstateFundCreate,
)
from app.service.asset_service import AssetService
from app.service.portfolio_service import PortfolioService

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


async def test_asset_writers_normalize_new_tickers_and_preserve_legacy_spelling(async_db):
    item = AdminAssetItem(
        type="national_stock", name="Petrobras", ticker=" petr4 ",
        current_price=Decimal("35.50"),
    )
    assert item.ticker == "PETR4"
    created = (await AssetService(async_db).upsert_many([item]))[0]
    assert created.ticker == "PETR4"

    legacy = NationalStockModel(
        name="Legacy spelling", ticker=" vale3 ", current_price=Decimal("60"),
        type_column="national_stock", quote_currency="BRL",
    )
    async_db.add(legacy)
    await async_db.commit()

    updated = (await AssetService(async_db).upsert_many([AdminAssetItem(
        type="national_stock", name="Updated name", ticker="VALE3",
        current_price=Decimal("61"),
    )]))[0]
    assert updated.ticker == " vale3 "
    assert updated.name == "Updated name"
    resolved = await PortfolioService(async_db)._get_asset(" VALE3 ")
    assert resolved.id == updated.id


async def test_get_or_create_keeps_existing_asset_and_rejects_incompatible_type(async_db):
    original = (await AssetService(async_db).upsert_many([AdminAssetItem(
        type="national_stock", name="Catalog name", ticker="PETR4",
        current_price=Decimal("35.50"), quote_currency="BRL",
    )]))[0]

    same, created = await AssetService(async_db).get_or_create(NationalStockCreate(
        name="Provider name differs", ticker=" petr4 ", current_price=Decimal("36"),
        quote_currency="BRL",
    ))
    assert created is False
    assert same.id == original.id
    assert (same.name, same.ticker, same.current_price) == (
        "Catalog name", "PETR4", Decimal("35.50"),
    )

    with pytest.raises(InvalidAssetQuoteMetadataError, match="Tipo de ativo existente"):
        await AssetService(async_db).get_or_create(RealEstateFundCreate(
            name="Different type", ticker="PETR4", current_price=Decimal("36"),
            quote_currency="BRL",
        ))
    assert await async_db.scalar(select(func.count()).select_from(AssetModel)) == 1


async def test_get_or_create_rejects_incompatible_currency_and_external_identity(async_db):
    service = AssetService(async_db)
    await service.upsert_many([AdminAssetItem(
        type="cryptocurrency", name="Bitcoin", ticker="BTC",
        current_price=Decimal("60000"), quote_currency="USD", price_provider="manual",
    )])
    with pytest.raises(InvalidAssetQuoteMetadataError, match="Moeda incompatível"):
        await service.get_or_create(CryptocurrencyCreate(
            name="Bitcoin", ticker="BTC", current_price=Decimal("61000"),
            quote_currency="BRL", price_provider="manual",
        ))

    await service.upsert_many([AdminAssetItem(
        type="national_stock", name="Petrobras", ticker="PETR4",
        current_price=Decimal("35"), quote_currency="BRL", price_provider="brapi",
        external_price_id="PETR4",
    )])
    with pytest.raises(InvalidAssetQuoteMetadataError, match="Identidade externa incompatível"):
        await service.get_or_create(NationalStockCreate(
            name="Petrobras", ticker="PETR4", current_price=Decimal("36"),
            quote_currency="BRL", price_provider="brapi", external_price_id="PETR4F",
        ))

    bitcoin = await service._find_by_identity("BTC")
    stock = await service._find_by_identity("PETR4")
    assert (bitcoin.quote_currency, bitcoin.current_price) == ("USD", Decimal("60000"))
    assert (stock.external_price_id, stock.current_price) == ("PETR4", Decimal("35"))


async def test_concurrent_get_or_create_returns_the_same_asset_and_keeps_transactions_usable(
    async_session_factory,
):
    barrier = asyncio.Barrier(2)

    async def register(name: str):
        async with async_session_factory() as session:
            service = AssetService(session)
            original_find = service._find_by_identity
            synchronized = False

            async def find_after_both_initial_reads(identity: str):
                nonlocal synchronized
                result = await original_find(identity)
                if not synchronized:
                    synchronized = True
                    await barrier.wait()
                return result

            service._find_by_identity = find_after_both_initial_reads
            async with session.begin():
                model, created = await service.get_or_create(NationalStockCreate(
                    name=name, ticker=" conc3 ", current_price=Decimal("10"),
                    quote_currency="BRL",
                ))
                assert session.in_transaction()
                await session.scalar(select(1))
                result = (model.id, created)
            return result

    results = await asyncio.wait_for(
        asyncio.gather(register("First name"), register("Second name")),
        timeout=15,
    )
    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]

    async with async_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AssetModel)) == 1


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
