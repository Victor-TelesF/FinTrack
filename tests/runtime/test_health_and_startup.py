import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app import main


class ProbeEngine:
    def __init__(self, *, error=None, delay=0):
        self.error = error
        self.delay = delay
        self.calls = 0
        self.open = 0

    @asynccontextmanager
    async def connect(self):
        self.calls += 1
        self.open += 1
        try:
            if self.error:
                raise self.error
            yield self
        finally:
            self.open -= 1

    async def execute(self, statement):
        assert str(statement) == "SELECT 1"
        await asyncio.sleep(self.delay)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "connect", "timeout"])
async def test_health_is_public_bounded_and_redacts_database_failures(monkeypatch, failure, caplog):
    engine = ProbeEngine(
        error=OperationalError("SELECT 1", {}, Exception("synthetic-private-password"))
        if failure == "connect" else None,
        delay=1 if failure == "timeout" else 0,
    )
    monkeypatch.setattr(main, "async_engine", engine)
    monkeypatch.setattr(main, "settings", SimpleNamespace(DATABASE_READY_TIMEOUT=0.02))
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://testserver") as client:
        live = await client.get("/health/live")
        assert live.status_code == 200 and live.json() == {"status": "alive"}
        assert engine.calls == 0
        ready = await client.get("/health/ready")
    assert ready.status_code == (503 if failure else 200)
    assert ready.json() == {"status": "unavailable" if failure else "ready"}
    assert engine.calls == 1 and engine.open == 0
    assert "synthetic-private-password" not in ready.text + caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_startup_needs_no_database_and_shutdown_closes_resources(monkeypatch, fail):
    from unittest.mock import AsyncMock

    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(main, "async_engine", engine)
    client = None
    try:
        async with LifespanManager(main.app):
            service = main.app.state.quote_service
            client = service._source._client
            assert not client.is_closed
            if fail:
                raise RuntimeError("synthetic")
    except RuntimeError:
        assert fail
    assert client.is_closed and service._closed
    assert not hasattr(main.app.state, "quote_service")
    engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("port", [None, "8123"])
def test_api_script_executes_only_uvicorn(tmp_path, port):
    result_path = tmp_path / "args"
    uvicorn = tmp_path / "uvicorn"
    uvicorn.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$PROBE_RESULT"\n')
    uvicorn.chmod(0o700)
    alembic = tmp_path / "alembic"
    alembic.write_text("#!/bin/sh\nexit 99\n")
    alembic.chmod(0o700)
    env = {**os.environ, "PATH": str(tmp_path), "PROBE_RESULT": str(result_path)}
    env.pop("PORT", None)
    if port:
        env["PORT"] = port
    subprocess.run(["/bin/sh", "start.sh"], env=env, check=True)
    assert result_path.read_text().splitlines() == [
        "app.main:app", "--host", "0.0.0.0", "--port", port or "8000", "--workers", "1",
    ]


def test_release_script_executes_migrations_and_propagates_failure(tmp_path):
    result_path = tmp_path / "args"
    alembic = tmp_path / "alembic"
    alembic.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$PROBE_RESULT"\nexit 42\n')
    alembic.chmod(0o700)
    result = subprocess.run(["/bin/sh", "release.sh"], env={
        **os.environ, "PATH": str(tmp_path), "PROBE_RESULT": str(result_path),
    })
    assert result.returncode == 42
    assert result_path.read_text().splitlines() == ["upgrade", "head"]
