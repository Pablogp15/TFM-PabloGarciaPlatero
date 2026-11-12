"""Pruebas unitarias del almacenamiento local de imágenes."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.base import StorageObjectNotFoundError
from app.storage.local import LocalImageStorage


async def test_roundtrip_and_idempotent_delete(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path)
    key = "projects/abc/imagen.bin"

    await storage.save(key, b"contenido")
    assert await storage.read(key) == b"contenido"

    await storage.delete(key)
    with pytest.raises(StorageObjectNotFoundError):
        await storage.read(key)

    # Borrar de nuevo no debe fallar.
    await storage.delete(key)


@pytest.mark.parametrize(
    "key",
    [
        "",
        "../fuera.bin",
        "projects/../../fuera.bin",
        "/ruta/absoluta.bin",
        "\\ruta\\absoluta.bin",
    ],
)
async def test_rejects_keys_outside_root(tmp_path: Path, key: str) -> None:
    storage = LocalImageStorage(tmp_path)

    with pytest.raises(ValueError):
        await storage.save(key, b"contenido")
