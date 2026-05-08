import json
import redis.asyncio as aioredis
from typing import Any
from app.core.config import settings


class CacheService:
    """
    Abstracción sobre Redis para el product-service.
    Centraliza la lógica de serialización, prefijos y TTL.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.prefix = settings.REDIS_PREFIX
        self.ttl = settings.CACHE_TTL

    def _make_key(self, key: str) -> str:

        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> dict | None:
        """
        Busca un valor en Redis.
        Retorna el dict si existe, None si no existe (cache miss).
        """
        full_key = self._make_key(key)
        value = await self.redis.get(full_key)

        if value is None:
            return None

        return json.loads(value.decode("utf-8"))

    async def set(self, key: str, value: Any) -> None:
        """
        Guarda un valor en Redis con el TTL configurado.
        """
        full_key = self._make_key(key)
        
        serialized = json.dumps(value, default=str)
        await self.redis.set(full_key, serialized, ex=self.ttl)

    async def delete(self, key: str) -> None:
        """
        Elimina una clave específica.
        Usado cuando se actualiza o elimina un producto.
        """
        full_key = self._make_key(key)
        await self.redis.delete(full_key)

    async def delete_pattern(self, pattern: str) -> None:
        """
        Elimina todas las claves que coincidan con el patrón.

        Elimina todas las listas cacheadas de productos.
        """
        full_pattern = self._make_key(pattern)
        keys = await self.redis.keys(full_pattern)
        if keys:
            await self.redis.delete(*keys)



redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """
    Inicializa la conexión a Redis.
    """
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=False
    )
    return redis_client


async def get_cache() -> CacheService:
    """
    Dependency de FastAPI para inyectar el CacheService.
    """
    return CacheService(redis_client)