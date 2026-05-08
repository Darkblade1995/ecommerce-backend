from fastapi import HTTPException, status
from app.models.product import Product, Category
from app.repositories.product_repository import ProductRepository, CategoryRepository
from app.core.cache import CacheService
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, CategoryCreate
)
import uuid


class ProductService:
    """
    Lógica de negocio del catálogo de productos.
    Orquesta el repository (PostgreSQL) y el cache (Redis).
    Regla: este archivo no importa nada de sqlalchemy ni de redis directamente.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        category_repo: CategoryRepository,
        cache: CacheService,
    ):
        self.product_repo = product_repo
        self.category_repo = category_repo
        self.cache = cache

    async def get_product(self, product_id: str) -> ProductResponse:
        """
        Cache-Aside Pattern:
        1. Busca en Redis
        2. Si no está, busca en PostgreSQL
        3. Guarda en Redis para próximas consultas
        """
        cache_key = f"product:{product_id}"


        cached = await self.cache.get(cache_key)
        if cached:

            return ProductResponse(**cached)


        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )


        response = ProductResponse.from_orm_with_category(product)


        await self.cache.set(cache_key, response.model_dump())

        return response

    async def get_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category_id: str | None = None,
        search: str | None = None,
    ) -> ProductListResponse:
        """
        Lista de productos con caché.
        La clave incluye todos los parámetros para
        cachear cada combinación de filtros por separado.
        """

        cache_key = f"product:list:p{page}:ps{page_size}"
        if category_id:
            cache_key += f":cat:{category_id}"
        if search:
            cache_key += f":s:{search}"

        cached = await self.cache.get(cache_key)
        if cached:
            return ProductListResponse(**cached)


        products, total = await self.product_repo.get_all(
            page=page,
            page_size=page_size,
            category_id=category_id,
            search=search,
        )

        items = [
            ProductResponse.from_orm_with_category(p)
            for p in products
        ]

        response = ProductListResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )

        await self.cache.set(cache_key, response.model_dump())

        return response

    async def create_product(
        self,
        data: ProductCreate,
        created_by: str
    ) -> ProductResponse:
        """
        Crear producto nuevo.
        Invalida todas las listas cacheadas porque
        el nuevo producto debe aparecer en ellas.
        """

        if data.category_id:
            category = await self.category_repo.get_by_id(data.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category {data.category_id} not found"
                )

        product = Product(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            price=data.price,
            stock=data.stock,
            category_id=data.category_id,
            image_url=data.image_url,
        )

        created = await self.product_repo.create(product)


        await self.cache.delete_pattern("product:list:*")

        return ProductResponse.from_orm_with_category(created)

    async def update_product(
        self,
        product_id: str,
        data: ProductUpdate,
    ) -> ProductResponse:
        """
        Actualizar producto.
        Invalida el caché del producto específico y las listas.
        """
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )


        if data.category_id:
            category = await self.category_repo.get_by_id(data.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category {data.category_id} not found"
                )

        update_data = data.model_dump(exclude_unset=True)
        updated = await self.product_repo.update(product, update_data)


        await self.cache.delete(f"product:{product_id}")

        await self.cache.delete_pattern("product:list:*")

        return ProductResponse.from_orm_with_category(updated)

    async def delete_product(self, product_id: str) -> None:
        """
        Soft delete: marca el producto como inactivo.
        Invalida su caché y todas las listas.
        """
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )

        await self.product_repo.soft_delete(product)


        await self.cache.delete(f"product:{product_id}")
        await self.cache.delete_pattern("product:list:*")

    async def create_category(
        self,
        data: CategoryCreate
    ):

        existing = await self.category_repo.get_by_name(data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category '{data.name}' already exists"
            )

        category = Category(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
        )

        return await self.category_repo.create(category)