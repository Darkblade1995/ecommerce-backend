from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional
import math


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: Decimal
    stock: int = 0
    category_id: str | None = None
    image_url: str | None = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @field_validator("stock")
    @classmethod
    def stock_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stock cannot be negative")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    stock: int | None = None
    category_id: str | None = None
    image_url: str | None = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: Decimal
    stock: int
    category_id: str | None
    category_name: str | None = None
    image_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_category(cls, product) -> "ProductResponse":
        """
        Constructor alternativo que extrae el nombre de la categoría
        de la relación SQLAlchemy antes de que la sesión se cierre.
        """
        data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "category_id": product.category_id,
            "category_name": product.category.name if product.category else None,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "created_at": product.created_at,
        }
        return cls(**data)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[ProductResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "ProductListResponse":
        pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}