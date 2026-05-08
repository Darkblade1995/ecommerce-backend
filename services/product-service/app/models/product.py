
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,     
        nullable=False,
        index=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    
    products = relationship(
        "Product",
        back_populates="category",
        lazy="select"    
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True      
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

  
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )


    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

   
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("categories.id"),
        nullable=True,
        index=True   
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


    category = relationship(
        "Category",
        back_populates="products",
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"