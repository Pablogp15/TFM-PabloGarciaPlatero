"""Esquemas de entrada y salida de la autenticación."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

# 12 caracteres como mínimo y 128 como máximo: el límite superior evita que una
# contraseña desmesurada consuma CPU en Argon2id.
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    display_name: DisplayName


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class UserRead(BaseModel):
    """Datos públicos del usuario. Nunca incluye el hash de la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime


class CsrfResponse(BaseModel):
    csrf_token: str
