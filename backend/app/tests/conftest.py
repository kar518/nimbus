"""Integration tests use a disposable PostgreSQL database, never the workspace database."""

import os
import subprocess
import uuid

import psycopg2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import worker_bootstrap_token
from app.db.session import get_db
from app.main import app
from app.services.scheduler_service import run_scheduling_cycle


@pytest.fixture(scope="session")
def test_database():
    name = "nimbus_test_" + uuid.uuid4().hex[:12]
    connection = psycopg2.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE " + name)
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"], env=dict(os.environ, POSTGRES_DB=name), check=True
        )
        copied = settings.model_copy(update={"POSTGRES_DB": name})
        yield copied.SQLALCHEMY_DATABASE_URI
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DROP DATABASE " + name + " WITH (FORCE)")
        connection.close()


@pytest_asyncio.fixture
async def session_factory(test_database):
    engine = create_async_engine(test_database, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        await db.execute(text("TRUNCATE artifacts, jobs, workers, users CASCADE"))
        await db.commit()
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    async def database_override():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = database_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin(client):
    response = await client.post(
        "/api/v1/auth/setup", json={"username": "test-admin", "password": "test-password-123"}
    )
    assert response.status_code == 200, response.text
    return client


@pytest_asyncio.fixture
async def worker(admin):
    response = await admin.post(
        "/api/v1/workers/register",
        headers={"Authorization": "Bearer " + worker_bootstrap_token()},
        json={
            "name": "test-worker",
            "cpu_capacity": 2,
            "memory_capacity_mb": 2048,
            "gpu_memory": 0,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return data["worker"], {"Authorization": "Bearer " + data["token"]}


@pytest.fixture
def schedule(session_factory):
    async def cycle():
        async with session_factory() as db:
            return await run_scheduling_cycle(db)

    return cycle
