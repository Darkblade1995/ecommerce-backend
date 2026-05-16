import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from app.core.config import settings
from app.middleware.rate_limiter import setup_limiter
from app.routers import users, products
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_limiter(app)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://tu-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(products.router)


@app.get("/health", tags=["Infrastructure"])
async def health_check():
    health = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "checks": {}
    }

    # Verifica user-service
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.USER_SERVICE_URL}/health")
            if resp.status_code == 200:
                health["checks"]["user_service"] = "healthy"
            else:
                health["checks"]["user_service"] = f"unhealthy: {resp.status_code}"
                health["status"] = "degraded"
    except Exception as e:
        health["checks"]["user_service"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Verifica product-service
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.PRODUCT_SERVICE_URL}/health")
            if resp.status_code == 200:
                health["checks"]["product_service"] = "healthy"
            else:
                health["checks"]["product_service"] = f"unhealthy: {resp.status_code}"
                health["status"] = "degraded"
    except Exception as e:
        health["checks"]["product_service"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"\n>>> ERROR: {traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )