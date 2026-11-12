"""Pruebas unitarias de las primitivas de seguridad."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    is_valid_csrf_token,
    verify_password,
)


def test_password_hash_uses_argon2id() -> None:
    password_hash = hash_password("una-contraseña-larga")

    assert password_hash.startswith("$argon2id$")
    assert "una-contraseña-larga" not in password_hash


def test_password_verification() -> None:
    password_hash = hash_password("una-contraseña-larga")

    assert verify_password("una-contraseña-larga", password_hash) is True
    assert verify_password("otra-contraseña-larga", password_hash) is False


def test_password_hash_is_salted() -> None:
    assert hash_password("misma-contraseña") != hash_password("misma-contraseña")


def test_corrupted_hash_is_rejected_without_raising() -> None:
    assert verify_password("cualquiera", "no-es-un-hash") is False


def test_access_token_roundtrip() -> None:
    user_id = uuid4()

    assert decode_access_token(create_access_token(user_id)) == user_id


def test_access_token_rejects_tampering() -> None:
    token = create_access_token(uuid4())
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}xx"

    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_access_token_rejects_expired_tokens() -> None:
    expired = create_access_token(uuid4(), now=datetime.now(UTC) - timedelta(hours=2))

    with pytest.raises(TokenError):
        decode_access_token(expired)


def test_access_token_rejects_garbage() -> None:
    with pytest.raises(TokenError):
        decode_access_token("esto.no.es-un-jwt")


def test_refresh_token_is_opaque_and_hash_is_stable() -> None:
    token = generate_refresh_token()

    assert len(token) >= 64
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert len(hash_refresh_token(token)) == 64
    assert hash_refresh_token(token) != hash_refresh_token(generate_refresh_token())


def test_csrf_token_is_signed() -> None:
    token = generate_csrf_token()
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")

    assert is_valid_csrf_token(token) is True
    assert is_valid_csrf_token(tampered) is False
    assert is_valid_csrf_token("sin-firma") is False
    assert is_valid_csrf_token("") is False
