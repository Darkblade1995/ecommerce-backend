import uuid
import httpx
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem, OrderEvent, OrderStatus, OrderEventType
from app.schemas.order import OrderCreate, OrderStatusUpdate, ProductValidation
from app.core.config import settings
from app.core import kafka


class OrderCommandHandler:
    """
    Maneja todas las operaciones de escritura del order-service.
    Cada método representa un Command que modifica el estado del sistema.

    Se registra un OrderEvent y se publica un evento en Kafka.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

   

    async def _validate_products(
        self,
        items: list
    ) -> dict[str, ProductValidation]:
        """
        Verifica que todos los productos existen y tienen stock.
        Retorna un dict {product_id: ProductValidation} con los datos
        de cada producto para construir los OrderItems.

        Hace las llamadas HTTP en paralelo para mayor velocidad.
        """
        async with httpx.AsyncClient() as client:
            validated = {}
            for item in items:
                try:
                    response = await client.get(
                        f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{item.product_id}",
                        timeout=5.0
                    )
                except httpx.ConnectError:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Product service unavailable"
                    )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {item.product_id} not found"
                    )

                product_data = response.json()
                product = ProductValidation(**product_data)

                if not product.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {product.id} is not available"
                    )

                if product.stock < item.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for {product.name}. "
                               f"Available: {product.stock}, requested: {item.quantity}"
                    )

                validated[item.product_id] = product

        return validated

    async def _get_order(self, order_id: str) -> Order:
        """Helper para obtener una orden con sus items y eventos."""
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.events)
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        return order

    async def _add_event(
        self,
        order_id: str,
        event_type: OrderEventType,
        event_data: dict | None = None,
        created_by: str = "system"
    ) -> None:
        """
        Registra un evento en order_events.
        Este es el corazón del Event Sourcing:
        cada cambio de estado genera un registro inmutable.
        """
        event = OrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type=event_type,
            event_data=event_data,
            created_by=created_by
        )
        self.db.add(event)
        await self.db.flush()

   

    async def create_order(
        self,
        data: OrderCreate,
        user_id: str
    ) -> Order:
        """
        Command: CreateOrder

        Flujo:
        1. Validar que todos los productos existen y tienen stock
        2. Calcular el total con precios actuales
        3. Crear la orden y sus items en PostgreSQL
        4. Registrar evento ORDER_CREATED
        5. Publicar evento en Kafka para otros servicios
        """
      
        validated_products = await self._validate_products(data.items)

       
        total = Decimal("0")
        for item in data.items:
            product = validated_products[item.product_id]
            subtotal = product.price * item.quantity
            total += subtotal

       
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=OrderStatus.PENDING,
            total=total,
            shipping_address=data.shipping_address,
            notes=data.notes,
        )
        self.db.add(order)
        await self.db.flush()

       
        order_items = []
        for item in data.items:
            product = validated_products[item.product_id]
            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order.id,
                product_id=item.product_id,
               
                product_name=product.name,
                quantity=item.quantity,
             
                unit_price=product.price,
                subtotal=product.price * item.quantity,
            )
            self.db.add(order_item)
            order_items.append(order_item)

        await self.db.flush()

       
        await self._add_event(
            order_id=order.id,
            event_type=OrderEventType.ORDER_CREATED,
            event_data={
                "total": str(total),
                "items": [
                    {
                        "product_id": i.product_id,
                        "product_name": i.product_name,
                        "quantity": i.quantity,
                        "unit_price": str(i.unit_price),
                    }
                    for i in order_items
                ]
            },
            created_by=user_id
        )


        await kafka.publish_order_created(
            order_id=order.id,
            user_id=user_id,
            total=float(total),
            items=[
                {
                    "product_id": i.product_id,
                    "quantity": i.quantity,
                    "price": str(i.unit_price)
                }
                for i in order_items
            ]
        )

        return order

    async def cancel_order(
        self,
        order_id: str,
        user_id: str,
        reason: str = "User requested cancellation"
    ) -> Order:
        """
        Command: CancelOrder

        Solo se puede cancelar si el estado es:
        PENDING, PAYMENT_PENDING, CONFIRMED, o PROCESSING.
        No se puede cancelar una orden ya enviada o entregada.
        """
        order = await self._get_order(order_id)


        if order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own orders"
            )


        cancellable_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
        ]
        if order.status not in cancellable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order in status {order.status}. "
                       f"Only orders in {[s.value for s in cancellable_statuses]} can be cancelled."
            )

        old_status = order.status.value
        order.status = OrderStatus.CANCELLED
        await self.db.flush()

        await self._add_event(
            order_id=order.id,
            event_type=OrderEventType.ORDER_CANCELLED,
            event_data={"reason": reason, "previous_status": old_status},
            created_by=user_id
        )

        await kafka.publish_order_cancelled(
            order_id=order.id,
            user_id=user_id,
            reason=reason
        )

        return order

    async def update_order_status(
        self,
        order_id: str,
        data: OrderStatusUpdate,
        updated_by: str = "system"
    ) -> Order:
        """
        Command: UpdateOrderStatus

        Usado internamente por el sistema cuando:
        - payment-service confirma el pago
        - warehouse procesa el envío
        - repartidor marca como entregado

        Valida que la transición de estado sea válida.
        """
        order = await self._get_order(order_id)

        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED],
            OrderStatus.PAYMENT_PENDING: [OrderStatus.CONFIRMED, OrderStatus.FAILED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: [],
            OrderStatus.FAILED: [],
        }

        allowed = valid_transitions.get(order.status, [])
        if data.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {order.status} to {data.status}. "
                       f"Allowed transitions: {[s.value for s in allowed]}"
            )

        old_status = order.status.value
        order.status = data.status
        await self.db.flush()


        status_to_event = {
            OrderStatus.PAYMENT_PENDING: OrderEventType.PAYMENT_INITIATED,
            OrderStatus.CONFIRMED: OrderEventType.ORDER_CONFIRMED,
            OrderStatus.PROCESSING: OrderEventType.ORDER_PROCESSING,
            OrderStatus.SHIPPED: OrderEventType.ORDER_SHIPPED,
            OrderStatus.DELIVERED: OrderEventType.ORDER_DELIVERED,
            OrderStatus.CANCELLED: OrderEventType.ORDER_CANCELLED,
            OrderStatus.FAILED: OrderEventType.PAYMENT_FAILED,
        }

        event_type = status_to_event.get(data.status)
        if event_type:
            await self._add_event(
                order_id=order.id,
                event_type=event_type,
                event_data={
                    "previous_status": old_status,
                    "notes": data.notes
                },
                created_by=updated_by
            )

        await kafka.publish_order_status_updated(
            order_id=order.id,
            old_status=old_status,
            new_status=data.status.value
        )

        return order