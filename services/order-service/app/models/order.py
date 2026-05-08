import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    String, Boolean, DateTime, Numeric,
    Integer, ForeignKey, Text, Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAYMENT_PENDING = "payment_pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderEventType(str, enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_PROCESSING = "ORDER_PROCESSING"
    ORDER_SHIPPED = "ORDER_SHIPPED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )


    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True    
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )


    shipping_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

   
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="select"
    )

    events = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.created_at",
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status} total={self.total}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id"),
        nullable=False,
        index=True
    )


    product_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False
    )


    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )


    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    order = relationship("Order", back_populates="items")

    def __repr__(self) -> str:
        return f"<OrderItem product={self.product_name} qty={self.quantity}>"


class OrderEvent(Base):
    """
    Log inmutable de todos los eventos de una orden.
    Implementa Event Sourcing: nunca se modifican ni eliminan registros.
    Solo se insertan nuevos eventos.
    """
    __tablename__ = "order_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    event_type: Mapped[OrderEventType] = mapped_column(
        SAEnum(OrderEventType),
        nullable=False
    )


    event_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="system"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    order = relationship("Order", back_populates="events")

    def __repr__(self) -> str:
        return f"<OrderEvent type={self.event_type} order={self.order_id}>"