import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app.core.config import settings

logger = logging.getLogger(__name__)



producer: AIOKafkaProducer | None = None



async def start_kafka_producer() -> AIOKafkaProducer:
    """
    Inicializa el producer de Kafka.
    Se llama en el startup de FastAPI.
    """
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,

        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),

        key_serializer=lambda k: k.encode("utf-8") if k else None,

        acks="all",
    )
    await producer.start()
    logger.info("Kafka producer started")
    return producer


async def stop_kafka_producer() -> None:
    """
    Cierra el producer limpiamente.
    Se llama en el shutdown de FastAPI.
    """
    global producer
    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped")




async def publish_event(
    topic: str,
    event_type: str,
    data: dict,
    key: str | None = None,
) -> None:
    """
    Publica un evento en un topic de Kafka.

    Estructura del evento:
    {
        "event_type": "ORDER_CREATED",
        "timestamp": "2026-01-01T10:00:00Z",
        "data": {
            "order_id": "123",
            "user_id": "abc",
            ...
        }
    }

    Esta estructura estándar permite que cualquier consumidor
    identifique el tipo de evento sin conocer el schema completo.
    """
    if not producer:
        logger.warning("Kafka producer not initialized, skipping event")
        return

    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.APP_NAME,
        "data": data,
    }

    try:
        await producer.send_and_wait(
            topic=topic,
            value=event,
            key=key,
        )
        logger.info(f"Event published: {event_type} to {topic}")
    except Exception as e:

        logger.error(f"Failed to publish event {event_type}: {e}")




async def publish_order_created(order_id: str, user_id: str, total: float, items: list) -> None:
    """
    Publica el evento OrderCreated.

    payment-service escucha esto para iniciar el proceso de pago.
    notification-service escucha esto para enviar confirmación.
    inventory-service escucha esto para reservar el stock.
    """
    await publish_event(
        topic=settings.KAFKA_TOPIC_ORDERS,
        event_type="ORDER_CREATED",
        data={
            "order_id": order_id,
            "user_id": user_id,
            "total": total,
            "items": items,
        },

        key=order_id,
    )


async def publish_order_cancelled(order_id: str, user_id: str, reason: str) -> None:
    """
    Publica el evento OrderCancelled.

    payment-service escucha esto para reembolsar si ya cobró.
    notification-service escucha esto para notificar al usuario.
    inventory-service escucha esto para liberar el stock reservado.
    """
    await publish_event(
        topic=settings.KAFKA_TOPIC_ORDERS,
        event_type="ORDER_CANCELLED",
        data={
            "order_id": order_id,
            "user_id": user_id,
            "reason": reason,
        },
        key=order_id,
    )


async def publish_order_status_updated(
    order_id: str,
    old_status: str,
    new_status: str
) -> None:
    await publish_event(
        topic=settings.KAFKA_TOPIC_ORDERS,
        event_type="ORDER_STATUS_UPDATED",
        data={
            "order_id": order_id,
            "old_status": old_status,
            "new_status": new_status,
        },
        key=order_id,
    )




def create_consumer(topics: list[str]) -> AIOKafkaConsumer:
    """
    Crea un consumer de Kafka para los topics especificados.

    El consumer group garantiza que si hay múltiples instancias
    del order-service, cada mensaje es procesado por solo una.
    """
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,

        value_deserializer=lambda v: json.loads(v.decode("utf-8")),

        auto_offset_reset="earliest",

        enable_auto_commit=True,
    )