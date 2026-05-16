import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core import kafka
from app.models import order as order_model
from app.api.v1 import orders
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)


async def consume_payment_events() -> None:
    consumer = kafka.create_consumer([settings.KAFKA_TOPIC_PAYMENTS])
    try:
        await consumer.start()
        logger.info("Kafka consumer started, listening to payments topic")
        async for message in consumer:
            try:
                event = message.value
                event_type = event.get("event_type")
                data = event.get("data", {})
                order_id = data.get("order_id")
                if not order_id:
                    continue
                logger.info(f"Received event: {event_type} for order {order_id}")
            except Exception as e:
                logger.error(f"Error processing payment event: {e}")
    except asyncio.CancelledError:
        logger.info("Kafka consumer task cancelled")
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    try:
        await kafka.start_kafka_producer()
        logger.info("Kafka producer ready")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start: {e}")
        logger.warning("Service will run without Kafka")

    consumer_task = None
    try:
        consumer_task = asyncio.create_task(
            consume_payment_events(),
            name="kafka-consumer"
        )
        logger.info("Kafka consumer task started")
    except Exception as e:
        logger.warning(f"Kafka consumer failed to start: {e}")

    yield

    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        logger.info("Kafka consumer task stopped")

    await kafka.stop_kafka_producer()
    await engine.dispose()
    logger.info("order-service shutdown complete")


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

app.include_router(orders.router)


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

    # Verifica Kafka producer
    try:
        if kafka.producer:
            health["checks"]["kafka"] = "healthy"
        else:
            health["checks"]["kafka"] = "not connected"
    except Exception as e:
        health["checks"]["kafka"] = f"unhealthy: {str(e)}"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)}
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )