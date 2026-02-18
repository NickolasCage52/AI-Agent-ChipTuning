import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """
    Use a single event loop for the whole test session.
    This avoids asyncpg/SQLAlchemy pool connections being tied to a different loop
    between async tests.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()

