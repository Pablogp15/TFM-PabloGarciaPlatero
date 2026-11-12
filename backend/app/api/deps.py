"""Dependencias compartidas por los routers."""

from __future__ import annotations

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.security import TokenError, decode_access_token, is_valid_csrf_token
from app.db.session import get_db
from app.models.user import User

DbSession = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(request: Request, session: DbSession) -> User:
    """Resuelve el usuario a partir de la cookie de acceso.

    La autorización se comprueba siempre en el servidor: el cliente no puede
    indicar qué usuario es.
    """
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise _unauthorized()

    try:
        user_id: UUID = decode_access_token(token)
    except TokenError as exc:
        raise _unauthorized() from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_csrf(request: Request) -> None:
    """Valida el patrón *double submit* firmado con HMAC.

    La cookie la establece el servidor y lleva una firma que el atacante no
    puede reproducir, de modo que no basta con inyectar una cookie propia.
    """
    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER)

    if not cookie_value or not header_value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF ausente",
        )

    if not hmac.compare_digest(cookie_value.encode(), header_value.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF inválido",
        )

    if not is_valid_csrf_token(cookie_value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF inválido",
        )
