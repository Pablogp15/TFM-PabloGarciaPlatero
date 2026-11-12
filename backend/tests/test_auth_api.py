"""Prueba de integración del flujo completo de autenticación.

Necesita una base de datos PostgreSQL con la extensión ``vector``. Se omite si
no se define ``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL no está definida: se omite la prueba con base de datos",
)

EMAIL = "pintor@example.com"
PASSWORD = "contrasena-muy-segura"
REGISTER_PAYLOAD = {"email": EMAIL, "password": PASSWORD, "display_name": "Pintor"}


def _set_cookie_header(response: Response, name: str) -> str:
    return next(
        header
        for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{name}=")
    )


def _csrf(client: AsyncClient) -> str:
    token = client.cookies.get("mp_csrf")
    assert token is not None
    return token


async def test_authentication_flow() -> None:
    assert TEST_DATABASE_URL is not None

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=application)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. El token CSRF es imprescindible para cualquier escritura.
            csrf_response = await client.get("/api/v1/auth/csrf")
            assert csrf_response.status_code == 200
            csrf_token = csrf_response.json()["csrf_token"]
            assert client.cookies.get("mp_csrf") == csrf_token

            no_csrf = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
            assert no_csrf.status_code == 403

            # Una cookie CSRF inventada no sirve aunque la cabecera coincida:
            # la firma HMAC del servidor no se puede reproducir.
            async with AsyncClient(transport=transport, base_url="http://test") as forger:
                forged_csrf = await forger.post(
                    "/api/v1/auth/register",
                    json=REGISTER_PAYLOAD,
                    headers={
                        "X-CSRF-Token": "inventado.firma",
                        "Cookie": "mp_csrf=inventado.firma",
                    },
                )
                assert forged_csrf.status_code == 403

            short_password = await client.post(
                "/api/v1/auth/register",
                json={"email": "otro@example.com", "password": "corta", "display_name": "Otro"},
                headers={"X-CSRF-Token": csrf_token},
            )
            assert short_password.status_code == 422

            # 2. Registro.
            registered = await client.post(
                "/api/v1/auth/register",
                json=REGISTER_PAYLOAD,
                headers={"X-CSRF-Token": csrf_token},
            )
            assert registered.status_code == 201
            body = registered.json()
            assert body["email"] == EMAIL
            assert body["display_name"] == "Pintor"
            assert "password" not in body and "password_hash" not in body

            access_cookie = _set_cookie_header(registered, "mp_access")
            assert "HttpOnly" in access_cookie
            assert "Path=/api" in access_cookie

            csrf_cookie = _set_cookie_header(registered, "mp_csrf")
            assert "HttpOnly" not in csrf_cookie

            assert client.cookies.get("mp_access") is not None
            assert client.cookies.get("mp_refresh") is not None

            # 3. El usuario autenticado se resuelve desde la cookie.
            me = await client.get("/api/v1/auth/me")
            assert me.status_code == 200
            assert me.json()["email"] == EMAIL

            # 4. No se permiten correos duplicados.
            duplicate = await client.post(
                "/api/v1/auth/register",
                json=REGISTER_PAYLOAD,
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert duplicate.status_code == 409

            # 5. Credenciales incorrectas.
            wrong_password = await client.post(
                "/api/v1/auth/login",
                json={"email": EMAIL, "password": "contrasena-incorrecta"},
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert wrong_password.status_code == 401

            # 6. Inicio de sesión correcto; el correo se normaliza.
            logged_in = await client.post(
                "/api/v1/auth/login",
                json={"email": EMAIL.upper(), "password": PASSWORD},
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert logged_in.status_code == 200
            first_refresh = client.cookies.get("mp_refresh")
            assert first_refresh is not None

            # 7. La rotación invalida el token anterior.
            refreshed = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert refreshed.status_code == 200
            second_refresh = client.cookies.get("mp_refresh")
            assert second_refresh is not None and second_refresh != first_refresh

            # 8. Reutilizar un token rotado revoca todas las sesiones.
            async with AsyncClient(transport=transport, base_url="http://test") as replayer:
                csrf_token = _csrf(client)
                replay_headers = {
                    "X-CSRF-Token": csrf_token,
                    "Cookie": f"mp_refresh={first_refresh}; mp_csrf={csrf_token}",
                }
                reuse = await replayer.post("/api/v1/auth/refresh", headers=replay_headers)
                assert reuse.status_code == 401

            revoked = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert revoked.status_code == 401

            # 9. Un token de acceso manipulado no autentica.
            async with AsyncClient(transport=transport, base_url="http://test") as forged:
                forged_me = await forged.get(
                    "/api/v1/auth/me",
                    headers={"Cookie": "mp_access=token-falso"},
                )
                assert forged_me.status_code == 401

            # 10. Cierre de sesión.
            logged_in_again = await client.post(
                "/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert logged_in_again.status_code == 200

            logged_out = await client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert logged_out.status_code == 204
            assert client.cookies.get("mp_access") is None
            assert client.cookies.get("mp_refresh") is None
            assert (await client.get("/api/v1/auth/me")).status_code == 401
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
