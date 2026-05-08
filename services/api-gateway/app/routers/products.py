from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from app.core.config import settings
from app.core.security import require_auth, optional_auth
from app.routers.users import proxy_request


router = APIRouter(prefix="/api", tags=["Products"])


def require_role(allowed_roles: list[str]):
    def check_role(payload: dict = Depends(require_auth)) -> dict:
        user_role = payload.get("role", "user")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized for this action"
            )
        return payload
    return check_role


@router.get("/products",
    dependencies=[Depends(RateLimiter(times=200, seconds=60))])
async def get_products(
    request: Request,
    payload: dict | None = Depends(optional_auth)
):
    extra_headers = {}
    if payload:
        extra_headers["X-User-ID"] = payload["sub"]
        extra_headers["X-User-Role"] = payload.get("role", "user")
    url = f"{settings.PRODUCT_SERVICE_URL}/api/v1/products"
    return await proxy_request(request, url, extra_headers)


@router.get("/products/{product_id}",
    dependencies=[Depends(RateLimiter(times=200, seconds=60))])
async def get_product(
    request: Request,
    product_id: str,
    payload: dict | None = Depends(optional_auth)
):
    extra_headers = {}
    if payload:
        extra_headers["X-User-ID"] = payload["sub"]
        extra_headers["X-User-Role"] = payload.get("role", "user")
    url = f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
    return await proxy_request(request, url, extra_headers)


@router.post("/products",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def create_product(
    request: Request,
    payload: dict = Depends(require_role(["merchant", "admin"]))
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.PRODUCT_SERVICE_URL}/api/v1/products"
    return await proxy_request(request, url, extra_headers)


@router.put("/products/{product_id}",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def update_product(
    request: Request,
    product_id: str,
    payload: dict = Depends(require_role(["merchant", "admin"]))
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
    return await proxy_request(request, url, extra_headers)


@router.delete("/products/{product_id}",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def delete_product(
    request: Request,
    product_id: str,
    payload: dict = Depends(require_role(["admin"]))
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
    return await proxy_request(request, url, extra_headers)