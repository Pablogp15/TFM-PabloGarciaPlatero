"""Lógica de negocio de la autenticación.

El router se limita a traducir errores a códigos HTTP; aquí viven las reglas de
registro, verificación de credenciales, emisión y rotación de tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.models.user import RefreshToken, User


class AuthError(Exception):
    """Error de autenticación con traducción directa a una respuesta HTTP."""


class EmailAlreadyRegisteredError(AuthError):
    """El correo ya pertenece a una cuenta."""


class InvalidCredentialsError(AuthError):
    """Correo o contraseña incorrectos, o cuenta deshabilitada."""


class InvalidRefreshTokenError(AuthError):
    """El token de refresco no existe, ha caducado o fue revocado."""


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    csrf_token: str


class AuthService:
    """Casos de uso de autenticación sobre una sesión de base de datos."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        normalized_email = email.strip().lower()

        exists = await self._session.scalar(
            select(User.id).where(func.lower(User.email) == normalized_email)
        )
        if exists is not None:
            raise EmailAlreadyRegisteredError

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        self._session.add(user)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Dos registros simultáneos con el mismo correo: el índice único
            # resuelve la carrera aunque la comprobación previa no la viera.
            await self._session.rollback()
            raise EmailAlreadyRegisteredError from exc

        tokens = await self._issue_tokens(user, user_agent)
        await self._session.commit()
        return user, tokens

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        normalized_email = email.strip().lower()
        user = await self._session.scalar(
            select(User).where(func.lower(User.email) == normalized_email)
        )

        if user is None:
            verify_dummy_password(password)
            raise InvalidCredentialsError

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InvalidCredentialsError

        tokens = await self._issue_tokens(user, user_agent)
        await self._session.commit()
        return user, tokens

    async def rotate(
        self,
        *,
        refresh_token: str,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        record = await self._session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token)
            )
        )
        if record is None:
            raise InvalidRefreshTokenError

        now = datetime.now(UTC)

        if record.revoked_at is not None:
            # Un token ya usado ha vuelto a aparecer: se asume robo o reuso y se
            # cierran todas las sesiones activas del usuario.
            await self._session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == record.user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            await self._session.commit()
            raise InvalidRefreshTokenError

        if record.expires_at <= now:
            raise InvalidRefreshTokenError

        user = await self._session.get(User, record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        record.revoked_at = now
        tokens = await self._issue_tokens(user, user_agent)
        await self._session.commit()
        return user, tokens

    async def logout(self, *, refresh_token: str | None) -> None:
        """Revoca el token presentado. Es idempotente."""
        if not refresh_token:
            return

        record = await self._session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token)
            )
        )
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self._session.commit()

    async def _issue_tokens(self, user: User, user_agent: str | None) -> TokenPair:
        settings = get_settings()
        raw_refresh_token = generate_refresh_token()

        self._session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(days=settings.refresh_token_ttl_days),
                user_agent=(user_agent or "")[:255] or None,
            )
        )

        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh_token,
            csrf_token=generate_csrf_token(),
        )
