import asyncio
import json
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base
from app.core import kafka
from app.models import order as order_model
from app.api.v1 import orders

logger = logging.getLogger(__name__)


# ─── Consumer task ────────────────────────────────────

async def consume_payment_events() -> None:
    """
    Background task que escucha eventos del topic 'payments'.
    Corre indefinidamente mientras la app está viva.

    Cuando llega un evento PAYMENT_CONFIRMED o PAYMENT_FAILED,
    actualiza el estado de la orden correspondiente.
    """
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

                
                if event_type == "PAYMENT_CONFIRMED":
                   
                    async with httpx_internal() as client:
                        await client.post(
                            f"http://localhost:{PORT}/api/v1/orders/{order_id}/payment-confirmed"
                        )

                elif event_type == "PAYMENT_FAILED":
                  
                    async with httpx_internal() as client:
                        await client.post(
                            f"http://localhost:{PORT}/api/v1/orders/{order_id}/payment-failed"
                        )

            except Exception as e:
                logger.error(f"Error processing payment event: {e}")
                logger.error(traceback.format_exc())

    except asyncio.CancelledError:
        
        logger.info("Kafka consumer task cancelled")
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


# ─── Lifespan ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────


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

    # ── SHUTDOWN ─────────────────────────────────────

  
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


# ─── App ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://tu-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router)


@app.get("/health", tags=["Infrastructure"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
    }


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