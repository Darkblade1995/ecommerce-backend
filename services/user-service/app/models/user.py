
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserRole(str, enum.Enum):

    USER = "user"
    ADMIN = "admin"
    MERCHANT = "merchant" 


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,

        default=lambda: str(uuid.uuid4())
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,     
        nullable=False,
        index=True       
    )

    
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole),       
        default=UserRole.USER, 
        nullable=False
    )


    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )


    google_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True
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

   

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"  
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"