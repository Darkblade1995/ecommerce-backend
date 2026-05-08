# ──────────────────────────────────────────────────────
# services/api-gateway/app/middleware/rate_limiter.py
# ──────────────────────────────────────────────────────

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from app.core.config import settings


async def setup_limiter(app: FastAPI) -> None:
    """
    Inicializa FastAPILimiter con Redis async.
    Se llama en el startup event de FastAPI.
    """
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis_client)