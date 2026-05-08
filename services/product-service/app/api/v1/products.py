from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.cache import get_cache, CacheService
from app.repositories.product_repository import (
    ProductRepository,
    CategoryRepository
)
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    CategoryCreate,
    CategoryResponse,
)


router = APIRouter(prefix="/api/v1", tags=["Products"])


def get_product_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
) -> ProductService:
    product_repo = ProductRepository(db)
    category_repo = CategoryRepository(db)
    return ProductService(
        product_repo=product_repo,
        category_repo=category_repo,
        cache=cache,
    )




@router.get("/products", response_model=ProductListResponse)
async def get_products(

    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Productos por página"),
    category_id: str | None = Query(default=None, description="Filtrar por categoría"),
    search: str | None = Query(default=None, description="Buscar por nombre"),
    service: ProductService = Depends(get_product_service),
):
    """
    Lista de productos con paginación y filtros opcionales.
    Usa caché de Redis para respuestas rápidas en consultas repetidas.
    """
    return await service.get_products(
        page=page,
        page_size=page_size,
        category_id=category_id,
        search=search,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):
    """
    Detalle de un producto específico.
    Cache-Aside: Redis primero, PostgreSQL si no está en caché.
    """
    return await service.get_product(product_id)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),

    x_user_id: str | None = None,
):
    """
    Crear un nuevo producto.
    Requiere rol merchant o admin (validado en el gateway).
    Invalida el caché de listas al crear.
    """
    return await service.create_product(
        data=data,
        created_by=x_user_id or "anonymous"
    )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    """
    Actualizar un producto existente.
    Invalida el caché del producto y las listas al actualizar.
    """
    return await service.update_product(
        product_id=product_id,
        data=data,
    )


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):
    """
    Soft delete: el producto queda inactivo, no se elimina de la BD.
    Invalida el caché del producto y las listas.
    """
    await service.delete_product(product_id)





@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    service: ProductService = Depends(get_product_service),
):
    categories = await service.category_repo.get_all()
    return categories


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_category(
    data: CategoryCreate,
    service: ProductService = Depends(get_product_service),
):
    return await service.create_category(data)