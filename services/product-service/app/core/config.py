
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "product-service"
    DEBUG: bool = False


    DATABASE_URL: str


    REDIS_URL: str = "redis://localhost:6379"


    REDIS_PREFIX: str = "product-service"


    CACHE_TTL: int = 300

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()