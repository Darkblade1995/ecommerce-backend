from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "api-gateway"
    DEBUG: bool = False


    USER_SERVICE_URL: str = "http://localhost:8001"
    PRODUCT_SERVICE_URL: str = "http://localhost:8002"
    ORDER_SERVICE_URL: str = "http://localhost:8003"


    REDIS_URL: str = "redis://localhost:6379"


    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"


    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()