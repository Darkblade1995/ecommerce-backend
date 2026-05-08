from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.user import User
from app.repositories.user_repository import UserRepository, RefreshTokenRepository
from app.schemas.user import UserCreate
from app.schemas.auth import TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class AuthService:
    """
    Lógica de negocio de autenticación.

    """

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ):

        self.user_repo = user_repo
        self.token_repo = token_repo

    async def register(self, data: UserCreate) -> User:

        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )


        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )

        created_user = await self.user_repo.create(user)



        return created_user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_email(email)


        if not user or not verify_password(password, user.hashed_password or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )


        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value
        )
        refresh_token = create_refresh_token(user_id=user.id)

        await self.token_repo.create(user_id=user.id, token=refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def refresh_access_token(self, refresh_token: str) -> str:

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        db_token = await self.token_repo.get_by_token(refresh_token)
        if not db_token or db_token.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or not found"
            )


        if db_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )


        user = await self.user_repo.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        return create_access_token(user_id=user.id, role=user.role.value)

    async def logout(self, refresh_token: str) -> None:

        await self.token_repo.revoke(refresh_token)


