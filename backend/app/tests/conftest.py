"""
Shared pytest fixtures.

Uses an httpx.AsyncClient against the ASGI app directly (no real network
socket), and a per-test transactional DB session that rolls back after
each test so tests never leak state into one another.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.main import app


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
def _dispose_engine_after_suite():
    yield
    import asyncio

    asyncio.get_event_loop().run_until_complete(engine.dispose())
