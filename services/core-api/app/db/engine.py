from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.settings import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


async_engine = create_engine()

