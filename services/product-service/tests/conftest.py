import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.core.database import Base, get_db
from app.core.cache import get_cache, CacheService

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def mock_cache():
    cache = MagicMock(spec=CacheService)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.delete_pattern = AsyncMock(return_value=True)
    return cache


@pytest_asyncio.fixture(scope="function")
async def client(db_session, mock_cache):
    async def override_get_db():
        yield db_session

    async def override_get_cache():
        return mock_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_category(db_session):
    from app.models.product import Category
    import uuid
    category = Category(
        id=str(uuid.uuid4()),
        name="Test Category",
        description="Test Description",
        is_active=True
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session, test_category):
    from app.models.product import Product
    import uuid
    from decimal import Decimal
    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product",
        description="Test Description",
        price=Decimal("99.99"),
        stock=10,
        category_id=test_category.id,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product