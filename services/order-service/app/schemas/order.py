from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus, OrderEventType




class OrderItemCreate(BaseModel):
    """Un producto dentro de la orden al momento de crearla."""
    product_id: str
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class OrderItemResponse(BaseModel):
    """Un producto dentro de la orden en la respuesta."""
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}




class OrderEventResponse(BaseModel):
    """Un evento del historial de la orden."""
    id: str
    event_type: OrderEventType
    event_data: dict | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}



class OrderCreate(BaseModel):
    """Lo que el cliente manda al crear una orden."""
    items: list[OrderItemCreate]
    shipping_address: str | None = None
    notes: str | None = None

    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Order must have at least one item")
        return v

    @model_validator(mode="after")
    def no_duplicate_products(self) -> "OrderCreate":
        """
        Verifica que no haya productos duplicados en la orden.
        """
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Duplicate products in order. "
                "Consolidate quantities in a single item."
            )
        return self

    @field_validator("items")
    @classmethod
    def max_items_per_order(cls, v: list) -> list:
        if len(v) > 50:
            raise ValueError("Order cannot have more than 50 items")
        return v


class OrderResponse(BaseModel):
    """La orden completa que retorna el API."""
    id: str
    user_id: str
    status: OrderStatus
    total: Decimal
    shipping_address: str | None
    notes: str | None
    items: list[OrderItemResponse]
    events: list[OrderEventResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Lista paginada de órdenes."""
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OrderStatusUpdate(BaseModel):
    """Para cambiar el estado de una orden."""
    status: OrderStatus
    notes: str | None = None



class ProductValidation(BaseModel):
    """
    verifica que un producto existe antes de crear la orden.
    """
    id: str
    name: str
    price: Decimal
    stock: int
    is_active: bool