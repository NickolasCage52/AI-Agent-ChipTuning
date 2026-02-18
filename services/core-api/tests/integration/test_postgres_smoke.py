import os

import asyncpg
import pytest


@pytest.mark.asyncio
async def test_postgres_connect_smoke():
    dsn = os.environ.get("ASYNC_DATABASE_URL")
    assert dsn, "ASYNC_DATABASE_URL must be set in test environment"
    # docker-compose uses SQLAlchemy async URL; asyncpg expects "postgresql://"
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        val = await conn.fetchval("select 1;")
        assert val == 1
    finally:
        await conn.close()

