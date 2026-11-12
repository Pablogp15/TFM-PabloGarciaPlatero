"""Primitivas criptográficas de la autenticación.

Concentra el hashing de contraseñas, la firma de los JWT, la generación de
tokens de refresco opacos y la firma HMAC de los tokens CSRF. Ninguna de estas
funciones depende de la base de datos ni de FastAPI.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

JWT_ALGORITHM: Final = "HS256"
ACCESS_TOKEN_TYPE: Final = "access"

_password_hasher = PasswordHash.recommended()

# Hash de descarte con el que se verifica una contraseña cuando el correo no
# existe, para que el tiempo de respuesta no revele si la cuenta está dada de
# alta.
_DUMMY_PASSWORD_HASH: Final = _password_hasher.hash(secrets.token_urlsafe(32))


class TokenError(Exception):
    """El token no es válido, ha expirado o no tiene el formato esperado."""


def hash_password(password: str) -> str:
    """Devuelve el hash Argon2id de la contraseña."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra su hash."""
    try:
        return _password_hasher.verify(password, password_hash)
    except Exception:
        # Un hash corrupto o de un formato desconocido equivale a credenciales
        # inválidas; nunca debe provocar un error 500.
        return False


def verify_dummy_password(password: str) -> None:
    """Consume el mismo tiempo que una verificación real.

    Se usa cuando el usuario no existe para no filtrar la existencia de una
    cuenta por diferencias de latencia.
    """
    verify_password(password, _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: UUID, *, now: datetime | None = None) -> str:
    """Firma un JWT de acceso de corta duración."""
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "jti": secrets.token_urlsafe(16),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Valida el JWT y devuelve el identificador de usuario.

    Se exigen las claims mínimas y el tipo de token para que un token de otro
    propósito no pueda reutilizarse como credencial de acceso.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Token de acceso inválido") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("Tipo de token incorrecto")

    try:
        return UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Identificador de usuario inválido") from exc


def generate_refresh_token() -> str:
    """Genera un token de refresco opaco con 384 bits de entropía."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash determinista del token de refresco.

    El token es aleatorio y de alta entropía, por lo que SHA-256 es suficiente
    y permite localizarlo por índice único.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _sign_csrf(value: str) -> str:
    return hmac.new(
        get_settings().secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_csrf_token() -> str:
    """Token CSRF firmado con el formato ``aleatorio.firma``."""
    raw = secrets.token_urlsafe(32)
    return f"{raw}.{_sign_csrf(raw)}"


def is_valid_csrf_token(value: str) -> bool:
    """Comprueba que el token CSRF conserve una firma HMAC válida."""
    raw, separator, signature = value.partition(".")
    if not separator or not raw or not signature:
        return False
    return hmac.compare_digest(_sign_csrf(raw), signature)
