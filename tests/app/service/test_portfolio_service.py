import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, select, text

from app.errors.exceptions import InvalidPortfolioTransactionError, PortfolioNotFoundError
from app.models import TransactionModel, UserModel, PortfolioModel
from app.schemas.asset_schema import AdminAssetItem
from app.schemas.portfolio_schema import PositionRead
from app.schemas.transaction_schema import TransactionCreate, TransactionRead
from app.service.asset_service import AssetService
from app.service.portfolio_service import PortfolioService
from domain.enums import TransactionType

pytestmark = pytest.mark.asyncio


def transaction(ticker="ABCD3", quantity="10"):
    return TransactionCreate(ticker=ticker, quantity=Decimal(quantity),
                             price=Decimal("30"), transaction_date=date(2026, 9, 25))


@pytest_asyncio.fixture
async def portfolio_data(async_session_factory, legacy_http_examples):
    async with async_session_factory() as db:
        user = UserModel(user_name="portfolio_service", hash_password="synthetic")
        portfolio = PortfolioModel(user=user)
        db.add(portfolio)
        await db.commit()
        ids = (portfolio.id_portfolio, user.user_id)
        await AssetService(db).upsert_many([
            AdminAssetItem.model_validate(item)
            for item in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]
        ])
        return ids


async def test_all_asset_types_serialize_after_close_with_constant_query_count(
    portfolio_data, async_session_factory, async_engine, legacy_http_examples
):
    portfolio_id, user_id = portfolio_data
    items = legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]
    for item in items:
        async with async_session_factory() as db:
            created = await PortfolioService(db).add_transaction(
                portfolio_id, user_id, transaction(item["ticker"]), TransactionType.BUY
            )
        assert TransactionRead.model_validate(created).asset.ticker == item["ticker"]

    queries = []
    def record(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(async_engine.sync_engine, "before_cursor_execute", record)
    try:
        async with async_session_factory() as db:
            service = PortfolioService(db)
            positions = await service.positions(user_id)
            assert len(queries) == 2  # Portfolio + history/assets/prices, regardless of tickers.
            history = await service.list_transactions(portfolio_id, user_id)
        before_serialization = len(queries)
        assert len([PositionRead.model_validate(item) for item in positions]) == 6
        assert len([TransactionRead.model_validate(item) for item in history]) == 6
        rebuilt = service._rebuild_domain_portfolio(portfolio_id, history)
        assert len(rebuilt.positions) == 6
        assert len(queries) == before_serialization
    finally:
        event.remove(async_engine.sync_engine, "before_cursor_execute", record)


@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_failed_write_rolls_back_and_releases_lock(
    portfolio_data, async_session_factory, monkeypatch, failure
):
    portfolio_id, user_id = portfolio_data
    async with async_session_factory() as db:
        async def fail_commit():
            raise failure("synthetic failure after flush")
        monkeypatch.setattr(db, "commit", AsyncMock(side_effect=fail_commit))
        with pytest.raises(failure):
            await PortfolioService(db).add_transaction(
                portfolio_id, user_id, transaction(), TransactionType.BUY
            )
        assert not db.in_transaction()
    async with async_session_factory() as db:
        assert list(await db.scalars(select(TransactionModel))) == []
        await asyncio.wait_for(PortfolioService(db).add_transaction(
            portfolio_id, user_id, transaction(), TransactionType.BUY
        ), timeout=5)


async def test_other_user_cannot_write_or_read_portfolio(portfolio_data, async_session_factory):
    portfolio_id, _ = portfolio_data
    async with async_session_factory() as db:
        service = PortfolioService(db)
        with pytest.raises(PortfolioNotFoundError):
            await service.add_transaction(portfolio_id, uuid4(), transaction(), TransactionType.BUY)
        assert not db.in_transaction()
        with pytest.raises(PortfolioNotFoundError):
            await service.list_transactions(portfolio_id, uuid4())
        assert list(await db.scalars(select(TransactionModel))) == []


async def test_concurrent_sales_wait_for_commit_then_recheck_balance(
    portfolio_data, async_session_factory, monkeypatch
):
    portfolio_id, user_id = portfolio_data
    async with async_session_factory() as db:
        await PortfolioService(db).add_transaction(
            portfolio_id, user_id, transaction(), TransactionType.BUY
        )

    first_ready = asyncio.Event()
    release_first = asyncio.Event()
    async with async_session_factory() as first, async_session_factory() as second:
        first_commit = first.commit
        async def held_commit():
            first_ready.set()
            await release_first.wait()
            await first_commit()
        monkeypatch.setattr(first, "commit", held_commit)
        second_pid = await second.scalar(text("SELECT pg_backend_pid()"))
        first_task = asyncio.create_task(PortfolioService(first).add_transaction(
            portfolio_id, user_id, transaction(quantity="7"), TransactionType.SELL
        ))
        second_task = None
        try:
            await asyncio.wait_for(first_ready.wait(), timeout=5)
            second_task = asyncio.create_task(PortfolioService(second).add_transaction(
                portfolio_id, user_id, transaction(quantity="7"), TransactionType.SELL
            ))
            async def wait_for_block():
                async with async_session_factory() as observer:
                    while not await observer.scalar(text(
                        "SELECT cardinality(pg_blocking_pids(:pid)) > 0"
                    ), {"pid": second_pid}):
                        await asyncio.sleep(0.01)
            await asyncio.wait_for(wait_for_block(), timeout=5)
            assert not second_task.done()
            release_first.set()
            await asyncio.wait_for(first_task, timeout=5)
            with pytest.raises(InvalidPortfolioTransactionError, match="Não é possivel vender mais do que possui"):
                await asyncio.wait_for(second_task, timeout=5)
            assert not second.in_transaction()
        finally:
            release_first.set()
            tasks = [task for task in (first_task, second_task) if task is not None]
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async with async_session_factory() as db:
        service = PortfolioService(db)
        history = await service.list_transactions(portfolio_id, user_id)
        assert [item.transaction_type for item in history] == [TransactionType.BUY, TransactionType.SELL]
        assert (await service.positions(user_id))[0]["quantity"] == Decimal("3")
