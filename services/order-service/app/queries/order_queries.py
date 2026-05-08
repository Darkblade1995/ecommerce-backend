import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.order import Order, OrderEvent, OrderStatus
from app.schemas.order import OrderListResponse, OrderResponse


class OrderQueryHandler:
    """
    Maneja todas las operaciones de lectura del order-service.
    Ningún método aquí modifica datos.
    Cada método está optimizado para su patrón de acceso específico.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _load_options(self):
        """
        Opciones de carga que usamos en todas las queries.
        selectinload para items y eventos porque son
        relaciones uno-a-muchos (más eficiente que joinedload).
        """
        return [
            selectinload(Order.items),
            selectinload(Order.events),
        ]

    async def get_by_id(
        self,
        order_id: str,
        user_id: str | None = None
    ) -> Order:
        """
        Obtiene una orden por su ID con todos sus items y eventos.

        Si user_id viene especificado, verifica que la orden
        pertenece a ese usuario. Los admins no pasan user_id.
        """
        result = await self.db.execute(
            select(Order)
            .options(*self._load_options())
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )


        if user_id and order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own orders"
            )

        return order

    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: OrderStatus | None = None,
    ) -> OrderListResponse:
        """
        Obtiene todas las órdenes de un usuario con paginación.
        Ordenadas por fecha de creación descendente (más reciente primero).

        Patrón de acceso optimizado para:
          WHERE user_id = 'abc'
          ORDER BY created_at DESC
          LIMIT 20 OFFSET 0
        """
        base_query = (
            select(Order)
            .options(*self._load_options())
            .where(Order.user_id == user_id)
        )

        if status_filter:
            base_query = base_query.where(Order.status == status_filter)


        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0


        offset = (page - 1) * page_size
        paginated = base_query.order_by(
            Order.created_at.desc()
        ).limit(page_size).offset(offset)

        result = await self.db.execute(paginated)
        orders = result.unique().scalars().all()

        pages = math.ceil(total / page_size) if page_size > 0 else 0

        return OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )

    async def get_all_admin(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: OrderStatus | None = None,
        user_id_filter: str | None = None,
    ) -> OrderListResponse:
        """
        Vista administrativa: todas las órdenes del sistema.
        Solo accesible para admins.
        Permite filtrar por status y por usuario.

        Patrón de acceso optimizado para:
          WHERE status = 'processing'
          ORDER BY created_at ASC   ← más antigua primero para procesar
        """
        base_query = select(Order).options(*self._load_options())


        filters = []
        if status_filter:
            filters.append(Order.status == status_filter)
        if user_id_filter:
            filters.append(Order.user_id == user_id_filter)
        if filters:
            base_query = base_query.where(and_(*filters))

        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
  
        paginated = base_query.order_by(
            Order.created_at.asc()
        ).limit(page_size).offset(offset)

        result = await self.db.execute(paginated)
        orders = result.unique().scalars().all()

        pages = math.ceil(total / page_size) if page_size > 0 else 0

        return OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )

    async def get_order_history(self, order_id: str) -> list[OrderEvent]:
        """
        Retorna el historial completo de eventos de una orden.
        Implementa la parte de lectura del Event Sourcing.

        Con este método puedes responder:
        - ¿Cuánto tardó en confirmarse el pago?
        - ¿A qué hora se envió?
        - ¿Quién canceló la orden y por qué?
        """
        result = await self.db.execute(
            select(OrderEvent)
            .where(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_orders_by_status(
        self,
        order_status: OrderStatus,
        limit: int = 100
    ) -> list[Order]:
        """
        Obtiene órdenes en un estado específico.
        Usado internamente por workers que procesan órdenes.

        Por ejemplo: un worker que busca órdenes en PROCESSING
        para verificar si ya fueron enviadas por el warehouse.
        """
        result = await self.db.execute(
            select(Order)
            .options(*self._load_options())
            .where(Order.status == order_status)
            .order_by(Order.created_at.asc())
            .limit(limit)
        )
        return list(result.unique().scalars().all())