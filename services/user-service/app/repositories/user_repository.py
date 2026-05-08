# ──────────────────────────────────────────────────────
# services/user-service/app/repositories/user_repository.py
# ──────────────────────────────────────────────────────

from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.token import RefreshToken
from app.core.config import settings


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        # Usado en login y en registro para verificar duplicados
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        # refresh trae los valores generados por PostgreSQL:
        # created_at, updated_at, y cualquier default de la BD
        await self.db.refresh(user)
        return user

    async def update(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        user.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(user)
        return user


class RefreshTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, token: str) -> RefreshToken:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.db.add(refresh_token)
        await self.db.flush()
        return refresh_token

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> None:
        db_token = await self.get_by_token(token)
        if db_token:
            db_token.revoked = True
            await self.db.flush()