import asyncio
import os
import socket

os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/valtherion_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import asyncpg
import httpx
import pytest_asyncio
import uvicorn
from sqlalchemy import text

from app.core.database import engine as app_engine
from app.main import app

import helpers
from helpers import register_player, update_player

TEST_DB_NAME = "valtherion_test"


async def _ensure_test_database():
    conn = await asyncpg.connect(
        user="postgres", password="postgres", database="postgres",
        host="127.0.0.1", port=5432,
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


async def _reset_schema():
    # Dispose the shared engine's pool BEFORE the schema drop. The in-process
    # uvicorn server and the tests both use app.core.database.engine, so the pool
    # holds several live connections; some carry RowExclusive locks from prior
    # requests. A DROP SCHEMA ... CASCADE against that same pool deadlocks on
    # those still-held locks. Disposing forces all pooled connections closed so
    # the reset runs on a single fresh connection and commits cleanly.
    await app_engine.dispose()
    async with app_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await app_engine.dispose()


async def _flush_redis():
    import redis.asyncio as aioredis
    client = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.flushdb()
    finally:
        await client.aclose()


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def server():
    await _ensure_test_database()
    await _reset_schema()
    await _flush_redis()

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server_obj = uvicorn.Server(config)
    task = asyncio.create_task(server_obj.serve())
    base_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as probe:
            for _ in range(300):
                if server_obj.started:
                    try:
                        if (await probe.get("/")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                await asyncio.sleep(0.05)
            else:
                raise RuntimeError("test server did not become ready")
        yield base_url
    finally:
        server_obj.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=15)
        except Exception:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest_asyncio.fixture(loop_scope="session")
async def client(server):
    async with httpx.AsyncClient(base_url=server, timeout=30) as c:
        yield c


@pytest_asyncio.fixture(loop_scope="session")
async def ws_base(server):
    return server.replace("http", "ws", 1)


@pytest_asyncio.fixture(loop_scope="session")
async def make_player(client):
    async def _make(**kwargs):
        return await register_player(client, **kwargs)
    return _make


@pytest_asyncio.fixture(loop_scope="session")
async def power_player(make_player):
    info = await make_player(job_class="Warrior")
    await update_player(
        info["username"],
        level=25,
        currency={"kupdun": 200000, "zirdun": 20000, "guldun": 2000},
        strength=1000,
        constitution=500,
        max_hp=5000,
        current_hp=5000,
    )
    return info
