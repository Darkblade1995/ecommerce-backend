import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate
from app.models.user import User, UserRole
from app.core.security import hash_password



def make_service(user_repo=None, token_repo=None) -> AuthService:

    return AuthService(
        user_repo=user_repo or AsyncMock(),
        token_repo=token_repo or AsyncMock(),
    )


def make_user(**kwargs) -> User:
    defaults = {
        "id": "user-uuid-123",
        "email": "juan@mail.com",
        "hashed_password": hash_password("pass1234"),
        "role": UserRole.USER,
        "is_active": True,
    }
    defaults.update(kwargs)
    user = MagicMock(spec=User)
    for key, value in defaults.items():
        setattr(user, key, value)
    return user




@pytest.mark.asyncio
async def test_register_exitoso():
    user_repo = AsyncMock()

    user_repo.get_by_email.return_value = None

    user_repo.create.return_value = make_user()

    service = make_service(user_repo=user_repo)
    data = UserCreate(email="juan@mail.com", password="pass1234")

    result = await service.register(data)


    user_repo.get_by_email.assert_called_once_with("juan@mail.com")

    user_repo.create.assert_called_once()
    assert result.email == "juan@mail.com"


@pytest.mark.asyncio
async def test_register_email_duplicado():
    user_repo = AsyncMock()

    user_repo.get_by_email.return_value = make_user()

    service = make_service(user_repo=user_repo)
    data = UserCreate(email="juan@mail.com", password="pass1234")


    with pytest.raises(HTTPException) as exc:
        await service.register(data)

    assert exc.value.status_code == 409

    user_repo.create.assert_not_called()




@pytest.mark.asyncio
async def test_login_exitoso():
    user_repo = AsyncMock()
    token_repo = AsyncMock()
    user_repo.get_by_email.return_value = make_user()

    service = make_service(user_repo=user_repo, token_repo=token_repo)
    result = await service.login("juan@mail.com", "pass1234")

    assert result.access_token is not None
    assert result.refresh_token is not None
    assert result.token_type == "bearer"

    token_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_login_email_inexistente():
    user_repo = AsyncMock()

    user_repo.get_by_email.return_value = None

    service = make_service(user_repo=user_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login("noexiste@mail.com", "pass1234")


    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_password_incorrecto():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = make_user()

    service = make_service(user_repo=user_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login("juan@mail.com", "password_equivocado")


    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_usuario_inactivo():
    user_repo = AsyncMock()

    user_repo.get_by_email.return_value = make_user(is_active=False)

    service = make_service(user_repo=user_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login("juan@mail.com", "pass1234")


    assert exc.value.status_code == 403