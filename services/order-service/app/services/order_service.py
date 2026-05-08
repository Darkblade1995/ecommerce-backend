from sqlalchemy.ext.asyncio import AsyncSession
from app.commands.order_commands import OrderCommandHandler
from app.queries.order_queries import OrderQueryHandler
from app.schemas.order import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    OrderListResponse,
)
from app.models.order import OrderStatus


class OrderService:

    def __init__(self, db: AsyncSession):
        self.command = OrderCommandHandler(db)
        self.query = OrderQueryHandler(db)

    async def create_order(
        self,
        data: OrderCreate,
        user_id: str
    ) -> OrderResponse:
        order = await self.command.create_order(data, user_id)
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total=order.total,
            shipping_address=order.shipping_address,
            notes=order.notes,
            items=[],
            events=[],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def cancel_order(
        self,
        order_id: str,
        user_id: str,
        reason: str = "User requested cancellation"
    ) -> OrderResponse:
        order = await self.command.cancel_order(order_id, user_id, reason)
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total=order.total,
            shipping_address=order.shipping_address,
            notes=order.notes,
            items=[],
            events=[],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def update_status(
        self,
        order_id: str,
        data: OrderStatusUpdate,
        updated_by: str = "system"
    ) -> OrderResponse:
        order = await self.command.update_order_status(
            order_id, data, updated_by
        )
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total=order.total,
            shipping_address=order.shipping_address,
            notes=order.notes,
            items=[],
            events=[],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def get_order(
        self,
        order_id: str,
        user_id: str | None = None
    ) -> OrderResponse:
        order = await self.query.get_by_id(order_id, user_id)
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total=order.total,
            shipping_address=order.shipping_address,
            notes=order.notes,
            items=[],
            events=[],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def get_user_orders(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: OrderStatus | None = None,
    ) -> OrderListResponse:
        return await self.query.get_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
        )

    async def get_all_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: OrderStatus | None = None,
        user_id_filter: str | None = None,
    ) -> OrderListResponse:
        return await self.query.get_all_admin(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            user_id_filter=user_id_filter,
        )

    async def get_order_history(self, order_id: str) -> list:
        return await self.query.get_order_history(order_id)