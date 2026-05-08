from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:

        if len(v) < 8:
            raise ValueError("Password must be at leaste 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at leaste one number")
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool     
    is_verified: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
            
