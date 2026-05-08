from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from app.models.product import Product, Category


class ProductRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, product_id: str) -> Product | None:
        result = await self.db.execute(
            select(Product)
            .options(joinedload(Product.category))

            .where(Product.id == product_id)
            .where(Product.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        category_id: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        """
        Retorna una tupla (productos, total).
        El total es el número de productos sin paginación,
        necesario para calcular el número de páginas.
        """

        base_query = (
            select(Product)
            .options(joinedload(Product.category))
            .where(Product.is_active == True)
        )


        if category_id:
            base_query = base_query.where(
                Product.category_id == category_id
            )

        if search:

            base_query = base_query.where(
                Product.name.ilike(f"%{search}%")
            )


        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0


        offset = (page - 1) * page_size
        paginated_query = base_query.limit(page_size).offset(offset)

        result = await self.db.execute(paginated_query)

        products = result.unique().scalars().all()

        return list(products), total

    async def create(self, product: Product) -> Product:
        self.db.add(product)
        await self.db.flush()

        return await self.get_by_id(product.id)

    async def update(self, product: Product, data: dict) -> Product:
        for key, value in data.items():
            setattr(product, key, value)
        product.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return await self.get_by_id(product.id)

    async def soft_delete(self, product: Product) -> None:

        product.is_active = False
        product.updated_at = datetime.now(timezone.utc)
        await self.db.flush()


class CategoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, category_id: str) -> Category | None:
        result = await self.db.execute(
            select(Category)
            .where(Category.id == category_id)
            .where(Category.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Category | None:
        result = await self.db.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.name)
        )
        return list(result.scalars().all())

    async def create(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category