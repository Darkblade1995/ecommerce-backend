import pytest


@pytest.mark.asyncio
async def test_register_crea_usuario(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "nuevo@mail.com",
        "password": "pass1234",
        "full_name": "Usuario Nuevo"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo@mail.com"
    assert data["full_name"] == "Usuario Nuevo"

    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_email_invalido(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "esto-no-es-un-email",
        "password": "pass1234"
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_corto(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "usuario@mail.com",
        "password": "corto"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_email_duplicado(client, test_user):

    response = await client.post("/api/v1/auth/register", json={
        "email": "test@mail.com",
        "password": "pass1234"
    })
    assert response.status_code == 409




@pytest.mark.asyncio
async def test_login_retorna_tokens(client, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@mail.com",
        "password": "testpass123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_credenciales_invalidas(client, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@mail.com",
        "password": "password_equivocado"
    })
    assert response.status_code == 401




@pytest.mark.asyncio
async def test_get_me_con_token_valido(client, test_user):

    login = await client.post("/api/v1/auth/login", json={
        "email": "test@mail.com",
        "password": "testpass123"
    })
    access_token = login.json()["access_token"]


    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@mail.com"


@pytest.mark.asyncio
async def test_get_me_sin_token(client):
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me_token_invalido(client):
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer token.falso.aqui"}
    )
    assert response.status_code == 401




@pytest.mark.asyncio
async def test_flujo_completo_register_login_perfil(client):

    register = await client.post("/api/v1/auth/register", json={
        "email": "flujo@mail.com",
        "password": "pass1234",
        "full_name": "Usuario Flujo"
    })
    assert register.status_code == 201


    login = await client.post("/api/v1/auth/login", json={
        "email": "flujo@mail.com",
        "password": "pass1234"
    })
    assert login.status_code == 200
    access_token = login.json()["access_token"]


    perfil = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert perfil.status_code == 200
    assert perfil.json()["email"] == "flujo@mail.com"