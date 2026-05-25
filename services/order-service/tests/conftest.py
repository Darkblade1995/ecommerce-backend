import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.database import Base, get_db

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
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

   
    with patch("app.core.kafka.publish_order_created", new_callable=AsyncMock), \
         patch("app.core.kafka.publish_order_cancelled", new_callable=AsyncMock), \
         patch("app.core.kafka.publish_order_status_updated", new_callable=AsyncMock):

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def mock_product():
    return {
        "id": "product-123",
        "name": "Test Product",
        "description": "Test",
        "price": "99.99",
        "stock": 10,
        "category_id": "cat-123",
        "category_name": "Test Category",
        "image_url": None,
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z"
    }


@pytest_asyncio.fixture(scope="function")
async def test_order(client, mock_product):
    with patch(
        "app.commands.order_commands.OrderCommandHandler._validate_products",
        new_callable=AsyncMock
    ) as mock_validate:
        from app.schemas.order import ProductValidation
        from decimal import Decimal
        mock_validate.return_value = {
            "product-123": ProductValidation(
                id="product-123",
                name="Test Product",
                price=Decimal("99.99"),
                stock=10,
                is_active=True
            )
        }

        response = await client.post("/api/v1/orders", json={
            "items": [{"product_id": "product-123", "quantity": 2}],
            "shipping_address": "Calle 123, Barranquilla",
            "notes": "Test order"
        })

    assert response.status_code == 201
    return response.json()