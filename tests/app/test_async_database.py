import asyncio
from contextlib import asynccontextmanager, nullcontext

import pytest
from asgi_lifespan import LifespanManager
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import UserModel

pytestmark = pytest.mark.asyncio


async def test_commit_preserves_loaded_attributes(async_db, async_session_factory):
    user = UserModel(user_name="async_user", hash_password="synthetic-hash")
    async_db.add(user)
    await async_db.commit()

    # Access after commit must not trigger an implicit database read.
    assert user.user_name == "async_user"
    async with async_session_factory() as verification_session:
        persisted = await verification_session.get(UserModel, user.user_id)
        assert persisted is not None
        assert persisted.user_name == user.user_name


@pytest.mark.parametrize("exit_error", [None, RuntimeError, asyncio.CancelledError])
async def test_dependency_releases_connection_and_rolls_back_uncommitted_work(
    async_session_factory, async_engine, exit_error
):
    expected_exit = pytest.raises(exit_error) if exit_error else nullcontext()
    with expected_exit:
        async with asynccontextmanager(get_db)() as session:
            session.add(UserModel(user_name="uncommitted", hash_password="synthetic-hash"))
            await session.flush()
            assert await session.scalar(select(func.count()).select_from(UserModel)) == 1
            if exit_error:
                raise exit_error()

    assert not session.in_transaction()
    assert async_engine.pool.checkedout() == 0
    async with async_session_factory() as verification_session:
        assert await verification_session.scalar(select(func.count()).select_from(UserModel)) == 0


async def test_http_dependency_uses_one_session_per_request_and_closes_on_error(
    test_app, async_engine, async_session_factory
):
    probe_app = FastAPI(lifespan=test_app.router.lifespan_context)
    sessions = []

    @probe_app.get("/probe")
    async def probe(
        fail: bool = False,
        session: AsyncSession = Depends(get_db),
        same_session: AsyncSession = Depends(get_db),
    ):
        sessions.append(session)
        session.add(UserModel(user_name="probe", hash_password="synthetic-hash"))
        await session.flush()
        if fail:
            raise RuntimeError("Synthetic request failure")
        return {"same_session": session is same_session}

    async with LifespanManager(probe_app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as client:
            for fail in (False, False, True):
                response = await client.get("/probe", params={"fail": fail})
                assert response.status_code == (500 if fail else 200)
                if not fail:
                    assert response.json() == {"same_session": True}
                assert not sessions[-1].in_transaction()
                assert async_engine.pool.checkedout() == 0

        assert len({id(session) for session in sessions}) == 3
        async with async_session_factory() as verification_session:
            assert await verification_session.scalar(select(func.count()).select_from(UserModel)) == 0


async def test_lifespan_disposes_opened_pool(test_app, async_engine):
    async_pool = async_engine.pool

    async with LifespanManager(test_app):
        async with async_engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
        assert async_pool.checkedin() == 1

    assert async_pool.checkedin() == 0
    assert async_engine.pool is not async_pool


@pytest.mark.parametrize("fail", [False, True])
async def test_lifespan_shares_quote_client_and_closes_it_on_exit(test_app, fail):
    from fastapi import Request
    from app.dependencies import get_quote_service

    with pytest.raises(RuntimeError, match="synthetic") if fail else nullcontext():
        async with LifespanManager(test_app):
            request = Request({"type": "http", "app": test_app})
            service = get_quote_service(request)
            assert get_quote_service(request) is service
            client = service._source._client
            assert not client.is_closed
            if fail:
                raise RuntimeError("synthetic")

    assert client.is_closed and service._closed
    assert not hasattr(test_app.state, "quote_service")
