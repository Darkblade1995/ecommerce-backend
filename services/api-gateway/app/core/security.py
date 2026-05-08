

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=True)


def decode_token(token: str) -> dict | None:
    """
    Decodifica y valida el JWT.
    Retorna el payload si es válido, None si no lo es.
    python-jose verifica firma y expiración automáticamente.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Dependency que protege endpoints en el gateway.
    Valida el token y retorna el payload completo.
    El payload contiene user_id y role, útiles para
    agregar headers internos antes de redirigir.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def optional_auth(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    )
) -> dict | None:
    """
    Dependency para endpoints que funcionan con o sin autenticación.
    Por ejemplo: ver productos no requiere login,
    pero si hay token lo procesamos para personalizar la respuesta.
    Retorna el payload si hay token válido, None si no hay token.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    return payload if payload and payload.get("type") == "access" else None