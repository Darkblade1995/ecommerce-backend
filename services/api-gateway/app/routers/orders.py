from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.core.config import settings
from app.core.security import require_auth
from app.routers.users import proxy_request


router = APIRouter(prefix="/api", tags=["Orders"])


@router.post("/orders",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def create_order(
    request: Request,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.ORDER_SERVICE_URL}/api/v1/orders"
    return await proxy_request(request, url, extra_headers)


@router.get("/orders/me",
    dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def get_my_orders(
    request: Request,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.ORDER_SERVICE_URL}/api/v1/orders/me"
    return await proxy_request(request, url, extra_headers)


@router.get("/orders/{order_id}",
    dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def get_order(
    request: Request,
    order_id: str,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.ORDER_SERVICE_URL}/api/v1/orders/{order_id}"
    return await proxy_request(request, url, extra_headers)


@router.post("/orders/{order_id}/cancel",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def cancel_order(
    request: Request,
    order_id: str,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.ORDER_SERVICE_URL}/api/v1/orders/{order_id}/cancel"
    return await proxy_request(request, url, extra_headers)


@router.get("/orders/{order_id}/history",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def get_order_history(
    request: Request,
    order_id: str,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.ORDER_SERVICE_URL}/api/v1/orders/{order_id}/history"
    return await proxy_request(request, url, extra_headers)