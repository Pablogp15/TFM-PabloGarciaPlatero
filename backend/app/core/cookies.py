"""Gestión de las cookies de autenticación.

Los tokens viajan en cookies ``HttpOnly`` para que JavaScript no pueda leerlos.
El token CSRF, en cambio, debe ser accesible desde el cliente porque se envía
de vuelta en la cabecera ``X-CSRF-Token`` (patrón *double submit*).
"""

from __future__ import annotations

from typing import Final

from fastapi import Response

from app.core.config import get_settings

ACCESS_COOKIE: Final = "mp_access"
REFRESH_COOKIE: Final = "mp_refresh"
CSRF_COOKIE: Final = "mp_csrf"
CSRF_HEADER: Final = "X-CSRF-Token"

_ACCESS_PATH: Final = "/api"
_REFRESH_PATH: Final = "/api/v1/auth"
_CSRF_PATH: Final = "/"


def _set_cookie(
    response: Response,
    *,
    name: str,
    value: str,
    path: str,
    max_age: int,
    http_only: bool,
) -> None:
    settings = get_settings()
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        path=path,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=http_only,
        samesite=settings.cookie_samesite,
    )


def _delete_cookie(response: Response, *, name: str, path: str) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=name,
        path=path,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def set_access_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    _set_cookie(
        response,
        name=ACCESS_COOKIE,
        value=token,
        path=_ACCESS_PATH,
        max_age=settings.access_token_ttl_minutes * 60,
        http_only=True,
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    _set_cookie(
        response,
        name=REFRESH_COOKIE,
        value=token,
        path=_REFRESH_PATH,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        http_only=True,
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    _set_cookie(
        response,
        name=CSRF_COOKIE,
        value=token,
        path=_CSRF_PATH,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        http_only=False,
    )


def clear_auth_cookies(response: Response) -> None:
    """Elimina las cookies de sesión respetando la ruta con la que se crearon."""
    _delete_cookie(response, name=ACCESS_COOKIE, path=_ACCESS_PATH)
    _delete_cookie(response, name=REFRESH_COOKIE, path=_REFRESH_PATH)
    _delete_cookie(response, name=CSRF_COOKIE, path=_CSRF_PATH)
