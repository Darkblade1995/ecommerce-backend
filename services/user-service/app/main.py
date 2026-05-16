from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.models import token as token_model
from app.api.v1 import auth, users
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://tu-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health", tags=["Infrastructure"])
async def health_check(db: AsyncSession = Depends(get_db)):
    health = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "checks": {}
    }

    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = "healthy"
    except Exception as e:
        health["checks"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "unhealthy"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)