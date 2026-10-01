import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.errors.exceptions import AssetCurrencyLockedError
from app.models import AssetModel, PortfolioModel, TransactionModel, UserModel
from app.schemas.asset_schema import AdminAssetItem
from app.schemas.transaction_schema import TransactionCreate
from app.service.asset_service import AssetService
from app.service.portfolio_service import PortfolioService
from domain.enums import TransactionType

pytestmark = pytest.mark.asyncio


async def test_currency_update_waits_for_first_purchase_then_rejects(async_session_factory, monkeypatch):
    item = AdminAssetItem(type="cryptocurrency", name="Bitcoin", ticker="BTC",
                          current_price=Decimal("100"), quote_currency="BRL")
    async with async_session_factory() as db:
        asset = (await AssetService(db).upsert_many([item]))[0]
        asset_id = asset.id
        user = UserModel(user_name="currency_race", hash_password="synthetic")
        portfolio = PortfolioModel(user=user)
        db.add(portfolio)
        await db.commit()
        portfolio_id, user_id = portfolio.id_portfolio, user.user_id

    first_ready, release_first = asyncio.Event(), asyncio.Event()
    async with async_session_factory() as purchase, async_session_factory() as update:
        commit = purchase.commit

        async def hold_commit():
            first_ready.set()
            await release_first.wait()
            await commit()

        monkeypatch.setattr(purchase, "commit", hold_commit)
        update_pid = await update.scalar(text("SELECT pg_backend_pid()"))
        purchase_task = asyncio.create_task(PortfolioService(purchase).add_transaction(
            portfolio_id, user_id,
            TransactionCreate(ticker="BTC", quantity=Decimal("1"), price=Decimal("90"),
                              transaction_date=date(2026, 10, 1)), TransactionType.BUY,
        ))
        update_task = None
        try:
            await asyncio.wait_for(first_ready.wait(), timeout=5)
            update_task = asyncio.create_task(AssetService(update).upsert_many([
                item.model_copy(update={"quote_currency": "USD"}),
            ]))

            async def wait_until_blocked():
                async with async_session_factory() as observer:
                    while not await observer.scalar(text(
                        "SELECT cardinality(pg_blocking_pids(:pid)) > 0"
                    ), {"pid": update_pid}):
                        await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_until_blocked(), timeout=5)
            assert not update_task.done()
            release_first.set()
            await asyncio.wait_for(purchase_task, timeout=5)
            with pytest.raises(AssetCurrencyLockedError):
                await asyncio.wait_for(update_task, timeout=5)
            assert not update.in_transaction()
        finally:
            release_first.set()
            tasks = [task for task in (purchase_task, update_task) if task is not None]
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async with async_session_factory() as db:
        assert (await db.get(AssetModel, asset_id)).quote_currency == "BRL"
        transactions = list(await db.scalars(select(TransactionModel)))
        assert len(transactions) == 1
        assert transactions[0].price == Decimal("90")
