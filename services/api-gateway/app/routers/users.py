

import uuid
import json
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Request, Response, Depends, status
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from app.core.config import settings
from app.core.security import require_auth


router = APIRouter(prefix="/api", tags=["Users & Auth"])


class RegisterBody(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


async def proxy_request(
    request: Request,
    target_url: str,
    extra_headers: dict = None,
    body_override: bytes = None
) -> Response:
    body = body_override if body_override is not None else await request.body()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ("host", "content-length")
    }
    headers["X-Request-ID"] = str(uuid.uuid4())

    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
                timeout=30.0,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
        except httpx.ConnectError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Service temporarily unavailable"}
            )
        except httpx.TimeoutException:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Service timeout"}
            )


# ─── Auth endpoints ───────────────────────────────────

@router.post("/auth/register",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def register(request: Request, body: RegisterBody):
    url = f"{settings.USER_SERVICE_URL}/api/v1/auth/register"
    return await proxy_request(
        request, url,
        body_override=json.dumps(body.model_dump()).encode()
    )


@router.post("/auth/login",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def login(request: Request, body: LoginBody):
    url = f"{settings.USER_SERVICE_URL}/api/v1/auth/login"
    return await proxy_request(
        request, url,
        body_override=json.dumps(body.model_dump()).encode()
    )


@router.post("/auth/refresh",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def refresh(request: Request, body: RefreshBody):
    url = f"{settings.USER_SERVICE_URL}/api/v1/auth/refresh"
    return await proxy_request(
        request, url,
        body_override=json.dumps(body.model_dump()).encode()
    )


@router.post("/auth/logout",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def logout(request: Request, body: RefreshBody):
    url = f"{settings.USER_SERVICE_URL}/api/v1/auth/logout"
    return await proxy_request(
        request, url,
        body_override=json.dumps(body.model_dump()).encode()
    )


# ─── User endpoints protegidos ────────────────────────

@router.get("/users/me",
    dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def get_me(
    request: Request,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user")
    }
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/me"
    return await proxy_request(request, url, extra_headers=extra_headers)


@router.patch("/users/me",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def update_me(
    request: Request,
    payload: dict = Depends(require_auth)
):
    extra_headers = {
        "X-User-ID": payload["sub"],
        "X-User-Role": payload.get("role", "user"),
    }
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/me"
    return await proxy_request(request, url, extra_headers=extra_headers)