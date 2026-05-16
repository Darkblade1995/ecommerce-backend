import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.cache import init_redis, redis_client
from app.models import product as product_model
from app.api.v1 import products
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_redis()
        print("Redis connected")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Service will run without cache")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables ready")
    yield
    if redis_client:
        await redis_client.close()
        print("Redis disconnected")
    await engine.dispose()
    print("Database pool closed")


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

app.include_router(products.router)


@app.get("/health", tags=["Infrastructure"])
async def health_check(db: AsyncSession = Depends(get_db)):
    health = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "checks": {}
    }

    # Verifica PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = "healthy"
    except Exception as e:
        health["checks"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "unhealthy"

    # Verifica Redis
    try:
        if redis_client:
            await redis_client.ping()
            health["checks"]["redis"] = "healthy"
        else:
            health["checks"]["redis"] = "not configured"
    except Exception as e:
        health["checks"]["redis"] = f"unhealthy: {str(e)}"
        health["status"] = "unhealthy"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        print(f"\n>>> ERROR:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)}
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )