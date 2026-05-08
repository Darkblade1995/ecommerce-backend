
from fastapi import APIRouter, Depends, status, Query, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.order_service import OrderService
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    OrderStatusUpdate,
)
from app.models.order import OrderStatus


router = APIRouter(prefix="/api/v1", tags=["Orders"])


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> dict:
    """
    Extrae la identidad del usuario desde los headers
    que el gateway agrega después de validar el JWT.

    En desarrollo directo (sin gateway) estos headers no vienen,
    así que usamos valores por defecto para facilitar las pruebas.
    """
    if not x_user_id:

        return {"user_id": "dev-user-id", "role": "admin"}

    return {"user_id": x_user_id, "role": x_user_role or "user"}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency que verifica que el usuario es admin.
    Si no lo es, lanza 403 Forbidden.
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ─── Endpoints de usuario ─────────────────────────────


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_order(
    data: OrderCreate,
    current_user: dict = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    """
    Crea una nueva orden.

    Flujo interno:
    1. Valida que todos los productos existen y tienen stock
    2. Calcula el total con precios actuales
    3. Persiste la orden en PostgreSQL
    4. Registra evento ORDER_CREATED
    5. Publica evento en Kafka para payment-service
    """
    return await service.create_order(
        data=data,
        user_id=current_user["user_id"]
    )


@router.get("/orders/me", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_status: OrderStatus | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    """
    Retorna las órdenes del usuario autenticado.
    Ordenadas por fecha de creación descendente.
    """
    return await service.get_user_orders(
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size,
        status_filter=order_status,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    """
    Retorna una orden específica.
    Un usuario solo puede ver sus propias órdenes.
    Un admin puede ver cualquier orden.
    """
    
    user_id = None if current_user["role"] == "admin" else current_user["user_id"]

    return await service.get_order(
        order_id=order_id,
        user_id=user_id
    )


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse
)
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    """
    Cancela una orden.
    Solo el dueño puede cancelar su propia orden.
    Solo se puede cancelar si el estado lo permite.
    """
    return await service.cancel_order(
        order_id=order_id,
        user_id=current_user["user_id"]
    )


# ─── Endpoints de admin ───────────────────────────────


@router.get("/orders", response_model=OrderListResponse)
async def get_all_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_status: OrderStatus | None = Query(default=None),
    user_id_filter: str | None = Query(default=None),
    current_user: dict = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
):
    """
    Vista administrativa de todas las órdenes del sistema.
    Solo accesible para admins.
    Ordenadas por fecha de creación ascendente (más antigua primero).
    """
    return await service.get_all_orders(
        page=page,
        page_size=page_size,
        status_filter=order_status,
        user_id_filter=user_id_filter,
    )


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    current_user: dict = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
):
    """
    Actualiza el estado de una orden.
    Solo admins. Valida que la transición sea válida.
    """
    return await service.update_status(
        order_id=order_id,
        data=data,
        updated_by=current_user["user_id"]
    )


@router.get("/orders/{order_id}/history")
async def get_order_history(
    order_id: str,
    current_user: dict = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
):
    """
    Retorna el historial completo de eventos de una orden.
    Implementa la lectura del Event Sourcing.
    Solo admins pueden ver el historial completo.
    """
    events = await service.get_order_history(order_id)
    return [
        {
            "event_type": e.event_type,
            "event_data": e.event_data,
            "created_by": e.created_by,
            "created_at": e.created_at,
        }
        for e in events
    ]


# ─── Webhooks internos del sistema ───────────────────


@router.post("/orders/{order_id}/payment-confirmed")
async def payment_confirmed(
    order_id: str,
    service: OrderService = Depends(get_order_service),
):
    """
    Webhook interno llamado por payment-service
    cuando un pago es confirmado exitosamente.

    En producción este endpoint estaría protegido
    con un secreto compartido entre servicios internos.
    """
    return await service.update_status(
        order_id=order_id,
        data=OrderStatusUpdate(status=OrderStatus.CONFIRMED),
        updated_by="payment-service"
    )


@router.post("/orders/{order_id}/payment-failed")
async def payment_failed(
    order_id: str,
    service: OrderService = Depends(get_order_service),
):
    """
    Webhook interno llamado por payment-service
    cuando un pago falla.
    """
    return await service.update_status(
        order_id=order_id,
        data=OrderStatusUpdate(status=OrderStatus.FAILED),
        updated_by="payment-service"
    )