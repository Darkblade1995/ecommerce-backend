
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "order-service"
    DEBUG: bool = False

    
    DATABASE_URL: str


    USER_SERVICE_URL: str = "http://localhost:8001"
    PRODUCT_SERVICE_URL: str = "http://localhost:8002"


    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"


    KAFKA_TOPIC_ORDERS: str = "orders"


    KAFKA_TOPIC_PAYMENTS: str = "payments"


    KAFKA_CONSUMER_GROUP: str = "order-service-group"


    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()