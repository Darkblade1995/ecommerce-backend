import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from testcontainers.postgres import PostgresContainer
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.security import hash_password

os.environ["DOCKER_HOST"] = "npipe:////./pipe/dockerDesktopLinuxEngine"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test_db",
    ) as postgres:
        yield postgres


@pytest_asyncio.fixture
async def db_engine(postgres_container):
    port = postgres_container.get_exposed_port(5432)
    url = f"postgresql+asyncpg://test:test@localhost:{port}/test_db"

    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    AsyncTestSession = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with AsyncTestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        email="test@mail.com",
        hashed_password=hash_password("testpass123"),
        full_name="Test User"
    )
    db_session.add(user)

    await db_session.commit()
    await db_session.refresh(user)
    return user



async def test_get_me_con_token_valido(client, test_user):
    login = await client.post("/api/v1/auth/login", json={
        "email": "test@mail.com",
        "password": "testpass123"
    })
    access_token = login.json()["access_token"]

    # Debug temporal
    debug = await client.get(
        "/api/v1/users/me/debug",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"\nDEBUG: {debug.json()}")

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200