from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.user_repository import UserRepository, RefreshTokenRepository
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])



def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(db)
    token_repo = RefreshTokenRepository(db)
    return AuthService(user_repo=user_repo, token_repo=token_repo)



@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service)
):
    user = await service.register(data)
    return user


@router.post("/login", response_model=TokenResponse)
async def logn(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    return await service.login(email=data.email, password=data.password)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service)
):
    access_token = await service.refresh_access_token(data.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service)
):
    await service.logout(data.refresh_token)



    

    


