"""Pruebas de integración de proyectos, esquema de color e imágenes.

Necesitan PostgreSQL con la extensión ``vector``. Se omiten si no se define
``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import io
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.enums import QualityMode
from app.models.generation import Generation
from app.services.catalog_seed import seed_catalog
from app.storage.deps import get_image_storage
from app.storage.local import LocalImageStorage

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL no está definida: se omite la prueba con base de datos",
)

EMAIL = "pintor@example.com"
OTHER_EMAIL = "otro@example.com"
PASSWORD = "contrasena-muy-segura"


@dataclass(frozen=True, slots=True)
class ApiContext:
    transport: ASGITransport
    session_factory: async_sessionmaker[AsyncSession]
    storage_root: Path


def _csrf(client: AsyncClient) -> str:
    token = client.cookies.get("mp_csrf")
    assert token is not None
    return token


async def _register(client: AsyncClient, email: str = EMAIL) -> None:
    csrf = await client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Pintor"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201


def _image_bytes(
    image_format: str = "PNG",
    *,
    size: tuple[int, int] = (80, 60),
    color: tuple[int, int, int] = (180, 60, 20),
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=image_format)
    return buffer.getvalue()


def _stored_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


async def _create_project(
    client: AsyncClient,
    name: str = "Proyecto de prueba",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/projects",
        json={"name": name, **extra},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def context(tmp_path: Path) -> AsyncIterator[ApiContext]:
    assert TEST_DATABASE_URL is not None

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_catalog(session)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    storage_root = tmp_path / "storage"
    storage = LocalImageStorage(storage_root)
    base_settings = get_settings()

    def override_settings() -> Settings:
        return base_settings.model_copy(update={"max_images_per_project": 2})

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_image_storage] = lambda: storage
    application.dependency_overrides[get_settings] = override_settings

    try:
        yield ApiContext(
            transport=ASGITransport(app=application),
            session_factory=session_factory,
            storage_root=storage_root,
        )
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def test_project_crud_and_ownership(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as owner:
        await _register(owner)

        # Sin CSRF no se permite escribir.
        assert (
            await owner.post("/api/v1/projects", json={"name": "Sin CSRF"})
        ).status_code == 403

        created = await _create_project(owner, "  Mi proyecto  ")
        assert created["name"] == "Mi proyecto"
        assert created["status"] == "draft"
        assert created["completed_at"] is None
        project_id = created["id"]

        assert (
            await owner.post(
                "/api/v1/projects",
                json={"name": "   "},
                headers={"X-CSRF-Token": _csrf(owner)},
            )
        ).status_code == 422

        listing = await owner.get("/api/v1/projects")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert (await owner.get("/api/v1/projects?q=mi")).json()["total"] == 1
        assert (await owner.get("/api/v1/projects?q=inexistente")).json()["total"] == 0

        detail = await owner.get(f"/api/v1/projects/{project_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == project_id

        updated = await owner.patch(
            f"/api/v1/projects/{project_id}",
            json={
                "name": "  Otro nombre  ",
                "description": "  descripción  ",
                "subject": "  Orco  ",
                "scale_mm": 32,
                "status": "painting",
            },
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert updated.status_code == 200
        body = updated.json()
        assert body["name"] == "Otro nombre"
        assert body["description"] == "descripción"
        assert body["subject"] == "Orco"
        assert body["scale_mm"] == 32
        assert body["status"] == "painting"

        completed = await owner.patch(
            f"/api/v1/projects/{project_id}",
            json={"status": "completed"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert completed.status_code == 200
        assert completed.json()["completed_at"] is not None

        reopened = await owner.patch(
            f"/api/v1/projects/{project_id}",
            json={"status": "painting"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert reopened.status_code == 200
        assert reopened.json()["completed_at"] is None

        assert (
            await owner.patch(
                f"/api/v1/projects/{project_id}",
                json={"status": "generating"},
                headers={"X-CSRF-Token": _csrf(owner)},
            )
        ).status_code == 422
        assert (
            await owner.patch(
                f"/api/v1/projects/{project_id}",
                json={},
                headers={"X-CSRF-Token": _csrf(owner)},
            )
        ).status_code == 422

        async with AsyncClient(
            transport=context.transport, base_url="http://test"
        ) as other:
            await _register(other, OTHER_EMAIL)

            assert (await other.get("/api/v1/projects")).json()["total"] == 0
            assert (
                await other.get(f"/api/v1/projects/{project_id}")
            ).status_code == 404
            assert (
                await other.patch(
                    f"/api/v1/projects/{project_id}",
                    json={"name": "Ajeno"},
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404
            assert (
                await other.delete(
                    f"/api/v1/projects/{project_id}",
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404

        deleted = await owner.delete(
            f"/api/v1/projects/{project_id}",
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert deleted.status_code == 204
        assert (await owner.get(f"/api/v1/projects/{project_id}")).status_code == 404
        assert (await owner.get("/api/v1/projects")).json()["total"] == 0


async def test_scheme_colors_replacement(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as owner:
        await _register(owner)
        project = await _create_project(owner)
        project_id = project["id"]

        catalog = await owner.get("/api/v1/paints?q=Abaddon&limit=1")
        paint = catalog.json()["items"][0]

        empty = await owner.get(f"/api/v1/projects/{project_id}/scheme-colors")
        assert empty.status_code == 200
        assert empty.json() == []

        payload = {
            "colors": [
                {"role": "primary", "paint_id": paint["id"]},
                {
                    "role": "accent",
                    "hex_override": "#a1b2c3",
                    "notes": "  detalle  ",
                },
            ]
        }

        assert (
            await owner.put(
                f"/api/v1/projects/{project_id}/scheme-colors",
                json=payload,
            )
        ).status_code == 403

        replaced = await owner.put(
            f"/api/v1/projects/{project_id}/scheme-colors",
            json=payload,
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert replaced.status_code == 200, replaced.text
        colors = replaced.json()
        assert [color["position"] for color in colors] == [0, 1]
        assert colors[0]["role"] == "primary"
        assert colors[0]["paint"]["id"] == paint["id"]
        assert colors[0]["effective_hex"] == paint["hex"]
        assert colors[1]["hex_override"] == "#A1B2C3"
        assert colors[1]["effective_hex"] == "#A1B2C3"
        assert colors[1]["notes"] == "detalle"
        assert colors[1]["paint"] is None

        current = await owner.get(f"/api/v1/projects/{project_id}/scheme-colors")
        assert current.status_code == 200
        assert [color["id"] for color in current.json()] == [
            color["id"] for color in colors
        ]

        unknown_paint = await owner.put(
            f"/api/v1/projects/{project_id}/scheme-colors",
            json={
                "colors": [
                    {"role": "primary", "paint_id": "00000000-0000-0000-0000-000000000000"}
                ]
            },
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert unknown_paint.status_code == 404

        no_color = await owner.put(
            f"/api/v1/projects/{project_id}/scheme-colors",
            json={"colors": [{"role": "primary"}]},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert no_color.status_code == 422

        async with AsyncClient(
            transport=context.transport, base_url="http://test"
        ) as other:
            await _register(other, OTHER_EMAIL)
            assert (
                await other.get(f"/api/v1/projects/{project_id}/scheme-colors")
            ).status_code == 404
            assert (
                await other.put(
                    f"/api/v1/projects/{project_id}/scheme-colors",
                    json={"colors": []},
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404

        cleared = await owner.put(
            f"/api/v1/projects/{project_id}/scheme-colors",
            json={"colors": []},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert cleared.status_code == 200
        assert cleared.json() == []


async def test_image_upload_dedupe_limit_and_cleanup(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as owner:
        await _register(owner)
        project = await _create_project(owner)
        project_id = project["id"]
        images_url = f"/api/v1/projects/{project_id}/images"

        png = _image_bytes("PNG")
        files = {"file": ("origen.png", png, "image/png")}

        assert (
            await owner.post(images_url, files=files, data={"kind": "source"})
        ).status_code == 403

        uploaded = await owner.post(
            images_url,
            files=files,
            data={"kind": "source"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert uploaded.status_code == 201, uploaded.text
        image = uploaded.json()
        assert image["kind"] == "source"
        assert image["mime_type"] == "image/png"
        assert (image["width"], image["height"]) == (80, 60)
        assert image["size_bytes"] > 0
        assert len(image["checksum"]) == 64
        assert image["url"] == f"/api/v1/projects/{project_id}/images/{image['id']}"

        duplicate = await owner.post(
            images_url,
            files=files,
            data={"kind": "source"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["id"] == image["id"]

        jpeg = _image_bytes("JPEG", size=(40, 30), color=(20, 100, 200))
        progress = await owner.post(
            images_url,
            files={"file": ("progreso.jpg", jpeg, "image/jpeg")},
            data={"kind": "progress"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert progress.status_code == 201, progress.text
        assert progress.json()["kind"] == "progress"

        listing = await owner.get(images_url)
        assert listing.status_code == 200
        assert listing.json()["total"] == 2
        filtered = await owner.get(f"{images_url}?kind=progress")
        assert filtered.json()["total"] == 1

        webp = _image_bytes("WEBP", size=(20, 20), color=(0, 0, 0))
        over_limit = await owner.post(
            images_url,
            files={"file": ("tercera.webp", webp, "image/webp")},
            data={"kind": "source"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert over_limit.status_code == 409

        gif = _image_bytes("GIF", size=(10, 10))
        invalid = await owner.post(
            images_url,
            files={"file": ("invalida.gif", gif, "image/gif")},
            data={"kind": "source"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert invalid.status_code == 422

        generated_kind = await owner.post(
            images_url,
            files={"file": ("generada.png", png, "image/png")},
            data={"kind": "generated"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert generated_kind.status_code == 422

        served = await owner.get(image["url"])
        assert served.status_code == 200
        assert served.headers["content-type"] == "image/png"
        assert served.headers["x-content-type-options"] == "nosniff"
        with Image.open(io.BytesIO(served.content)) as stored:
            assert stored.size == (80, 60)

        async with AsyncClient(
            transport=context.transport, base_url="http://test"
        ) as other:
            await _register(other, OTHER_EMAIL)
            assert (await other.get(image["url"])).status_code == 404
            assert (await other.get(images_url)).status_code == 404
            assert (
                await other.delete(
                    f"{images_url}/{image['id']}",
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404

        # Una imagen usada como origen de una generación no se puede borrar.
        async with context.session_factory() as session:
            generation = Generation(
                project_id=UUID(project_id),
                source_image_id=UUID(image["id"]),
                model_name="qwen-image-edit",
                prompt="prueba",
                quality=QualityMode.DRAFT,
            )
            session.add(generation)
            await session.commit()
            generation_id = generation.id

        in_use = await owner.delete(
            f"{images_url}/{image['id']}",
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert in_use.status_code == 409

        async with context.session_factory() as session:
            stored_generation = await session.get(Generation, generation_id)
            assert stored_generation is not None
            await session.delete(stored_generation)
            await session.commit()

        assert len(_stored_files(context.storage_root)) == 2

        deleted = await owner.delete(
            f"{images_url}/{image['id']}",
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert deleted.status_code == 204
        assert (await owner.get(image["url"])).status_code == 404
        assert (await owner.get(images_url)).json()["total"] == 1
        assert len(_stored_files(context.storage_root)) == 1

        # El borrado del proyecto debe limpiar también las imágenes restantes
        # y las generaciones que las referencian.
        replacement_png = _image_bytes("PNG", size=(30, 30), color=(10, 10, 10))
        replacement = await owner.post(
            images_url,
            files={"file": ("replacement.png", replacement_png, "image/png")},
            data={"kind": "source"},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert replacement.status_code == 201, replacement.text

        async with context.session_factory() as session:
            cascade_generation = Generation(
                project_id=UUID(project_id),
                source_image_id=UUID(replacement.json()["id"]),
                model_name="qwen-image-edit",
                prompt="prueba de cascada",
                quality=QualityMode.DRAFT,
            )
            session.add(cascade_generation)
            await session.commit()
            cascade_generation_id = cascade_generation.id

        assert len(_stored_files(context.storage_root)) == 2

        project_deleted = await owner.delete(
            f"/api/v1/projects/{project_id}",
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert project_deleted.status_code == 204
        assert _stored_files(context.storage_root) == []

        async with context.session_factory() as session:
            assert await session.get(Generation, cascade_generation_id) is None
