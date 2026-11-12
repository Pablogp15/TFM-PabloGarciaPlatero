"""Pruebas de integración de la cola de generación de imágenes.

Necesitan PostgreSQL con la extensión ``vector``. Se omiten si no se define
``TEST_DATABASE_URL``. El trabajador se ejecuta con ``StubGenerator`` para no
depender de la GPU.
"""

from __future__ import annotations

import io
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import httpx
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
from app.models.generation import Generation
from app.models.project import ProjectImage
from app.services.catalog_seed import seed_catalog
from app.services.generator import HttpGenerator, ImageGenerator, StubGenerator
from app.services.image_validation import ImageValidator
from app.storage.deps import get_image_storage
from app.storage.local import LocalImageStorage
from app.worker.loop import GenerationWorker

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL no está definida: se omite la prueba con base de datos",
)

EMAIL = "pintor@example.com"
OTHER_EMAIL = "otro@example.com"
PASSWORD = "contrasena-muy-segura"
MODEL_NAME = "Qwen-Image-Edit-2511"


@dataclass(frozen=True, slots=True)
class ApiContext:
    transport: ASGITransport
    session_factory: async_sessionmaker[AsyncSession]
    storage: LocalImageStorage
    settings: Settings


def _csrf(client: AsyncClient) -> str:
    token = client.cookies.get("mp_csrf")
    assert token is not None
    return token


async def _register(client: AsyncClient, email: str = EMAIL) -> None:
    assert (await client.get("/api/v1/auth/csrf")).status_code == 200
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Pintor"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201, response.text


def _image_bytes(
    image_format: str = "PNG",
    *,
    size: tuple[int, int] = (512, 512),
    color: tuple[int, int, int] = (180, 60, 20),
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=image_format)
    return buffer.getvalue()


async def _create_project(client: AsyncClient, name: str = "Proyecto F4") -> str:
    response = await client.post(
        "/api/v1/projects",
        json={"name": name},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _upload_source(client: AsyncClient, project_id: str) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/images",
        files={"file": ("origen.png", _image_bytes(), "image/png")},
        data={"kind": "source"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _build_worker(context: ApiContext, generator: ImageGenerator | None = None) -> GenerationWorker:
    return GenerationWorker(
        session_factory=context.session_factory,
        storage=context.storage,
        validator=ImageValidator(
            max_bytes=context.settings.generation_max_output_bytes,
            max_pixels=context.settings.max_image_pixels,
            max_dimension=context.settings.max_image_dimension,
        ),
        generator=generator or StubGenerator(model_name=MODEL_NAME),
        settings=context.settings,
    )


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

    storage = LocalImageStorage(tmp_path / "storage")
    settings = get_settings().model_copy(
        update={
            "generation_provider": "stub",
            "generation_service_token": "",
            "generation_max_active_per_project": 1,
            "generation_max_per_project": 10,
            "generation_max_output_bytes": 20 * 1024 * 1024,
        }
    )

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_image_storage] = lambda: storage
    application.dependency_overrides[get_settings] = lambda: settings

    try:
        yield ApiContext(
            transport=ASGITransport(app=application),
            session_factory=session_factory,
            storage=storage,
            settings=settings,
        )
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def test_generation_flow_end_to_end(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as client:
        await _register(client)
        project_id = await _create_project(client)
        source_id = await _upload_source(client, project_id)
        generations_url = f"/api/v1/projects/{project_id}/generations"

        payload = {
            "source_image_id": source_id,
            "prompt": "  Pinta la miniatura como un vampiro  ",
            "quality": "draft",
        }

        # Escribir exige token CSRF.
        assert (await client.post(generations_url, json=payload)).status_code == 403

        created = await client.post(
            generations_url,
            json=payload,
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert created.status_code == 202, created.text
        generation = created.json()
        generation_id = generation["id"]
        assert generation["status"] == "queued"
        assert generation["progress_stage"] == "queued"
        assert generation["progress_percent"] == 0
        assert generation["provider"] == "stub"
        assert generation["prompt"] == "Pinta la miniatura como un vampiro"
        assert generation["params"]["num_inference_steps"] == 20
        assert generation["params"]["width"] == 768
        assert generation["params"]["height"] == 768
        assert generation["result_url"] is None

        # Una segunda generación activa en el mismo proyecto se rechaza.
        blocked = await client.post(
            generations_url,
            json=payload,
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert blocked.status_code == 409

        worker = _build_worker(context)
        assert await worker.process_next() is True
        assert await worker.process_next() is False

        finished = await client.get(f"/api/v1/generations/{generation_id}")
        assert finished.status_code == 200, finished.text
        result = finished.json()
        assert result["status"] == "succeeded"
        assert result["progress_stage"] == "done"
        assert result["progress_percent"] == 100
        assert result["result_image_id"] is not None
        assert result["result_url"] == (
            f"/api/v1/projects/{project_id}/images/{result['result_image_id']}"
        )
        assert result["job_id"].startswith("stub-")
        assert result["inference_ms"] >= 0

        generated = await client.get(result["result_url"])
        assert generated.status_code == 200
        assert generated.headers["content-type"] == "image/png"
        with Image.open(io.BytesIO(generated.content)) as image:
            assert image.size == (768, 768)

        # Se permiten más de tres generaciones en una hora si cada trabajo
        # anterior terminó y el proyecto no ha alcanzado su cuota total.
        for _ in range(3):
            additional = await client.post(
                generations_url,
                json=payload,
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert additional.status_code == 202, additional.text
            assert await worker.process_next()

        images = await client.get(f"/api/v1/projects/{project_id}/images?kind=generated")
        assert images.status_code == 200
        assert images.json()["total"] == 4

        project = await client.get(f"/api/v1/projects/{project_id}")
        assert project.json()["status"] == "ready"

        listing = await client.get(generations_url)
        assert listing.status_code == 200
        assert listing.json()["total"] == 4


async def test_http_worker_persists_result(context: ApiContext) -> None:
    """El trabajador HTTP guarda imagen y métricas en PostgreSQL y almacenamiento."""
    import base64
    import json

    submitted: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Internal-Token"] == "test-internal-token"
        if request.method == "POST":
            submitted.append(json.loads(request.content))
            return httpx.Response(202, json={"job_id": "http-test"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, content=_image_bytes(color=(20, 40, 180)))
        return httpx.Response(
            200,
            json={
                "status": "succeeded",
                "stage": "done",
                "percent": 100,
                "model_name": MODEL_NAME,
                "inference_ms": 123,
                "model_load_ms": 0,
            },
        )

    settings = context.settings.model_copy(
        update={"generation_service_token": "test-internal-token"}
    )
    generator = HttpGenerator(settings, transport=httpx.MockTransport(handler))
    async with AsyncClient(transport=context.transport, base_url="http://test") as client:
        await _register(client)
        project_id = await _create_project(client)
        source_id = await _upload_source(client, project_id)
        response = await client.post(
            f"/api/v1/projects/{project_id}/generations",
            json={"source_image_id": source_id, "prompt": "Paint blue", "seed": 42},
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert response.status_code == 202
        assert await _build_worker(context, generator).process_next()
        result = (await client.get(f"/api/v1/generations/{response.json()['id']}")).json()
        assert result["status"] == "succeeded"
        assert result["provider"] == "qwen-local"
        assert result["inference_ms"] == 123
        assert result["job_id"] == "http-test"
        assert (await client.get(result["result_url"])).status_code == 200
        assert submitted[0]["prompt"] == "Paint blue"
        assert submitted[0]["seed"] == 42
        assert base64.b64decode(submitted[0]["source_image_b64"])


async def test_generation_validation_ownership_and_cancel(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as client:
        await _register(client)
        project_id = await _create_project(client)
        source_id = await _upload_source(client, project_id)
        generations_url = f"/api/v1/projects/{project_id}/generations"
        csrf = {"X-CSRF-Token": _csrf(client)}

        # Una imagen que no es de origen no puede usarse como base.
        progress_image = await client.post(
            f"/api/v1/projects/{project_id}/images",
            files={"file": ("progreso.png", _image_bytes(size=(64, 64)), "image/png")},
            data={"kind": "progress"},
            headers=csrf,
        )
        assert progress_image.status_code == 201, progress_image.text
        invalid_source = await client.post(
            generations_url,
            json={"source_image_id": progress_image.json()["id"], "prompt": "prueba"},
            headers=csrf,
        )
        assert invalid_source.status_code == 422

        # Un prompt vacío no pasa la validación del esquema.
        assert (
            await client.post(
                generations_url,
                json={"source_image_id": source_id, "prompt": "   "},
                headers=csrf,
            )
        ).status_code == 422

        created = await client.post(
            generations_url,
            json={
                "source_image_id": source_id,
                "prompt": "acabado final",
                "quality": "final",
                "num_inference_steps": 12,
            },
            headers=csrf,
        )
        assert created.status_code == 202, created.text
        generation = created.json()
        # Los valores explícitos ganan al preset de calidad.
        assert generation["params"]["num_inference_steps"] == 12
        assert generation["params"]["width"] == 1024
        assert generation["params"]["height"] == 1024

        async with AsyncClient(transport=context.transport, base_url="http://test") as other:
            await _register(other, OTHER_EMAIL)
            assert (await other.get(f"/api/v1/generations/{generation['id']}")).status_code == 404
            assert (
                await other.post(
                    f"/api/v1/generations/{generation['id']}/cancel",
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404
            assert (await other.get(generations_url)).status_code == 404

        cancelled = await client.post(
            f"/api/v1/generations/{generation['id']}/cancel",
            headers=csrf,
        )
        assert cancelled.status_code == 202, cancelled.text
        assert cancelled.json()["status"] == "cancelled"

        # Ya terminó: no se puede volver a cancelar.
        assert (
            await client.post(
                f"/api/v1/generations/{generation['id']}/cancel",
                headers=csrf,
            )
        ).status_code == 409

        # Tras cancelar, el proyecto vuelve a admitir otra generación.
        again = await client.post(
            generations_url,
            json={"source_image_id": source_id, "prompt": "otra prueba"},
            headers=csrf,
        )
        assert again.status_code == 202, again.text


async def test_generation_missing_source_fails_cleanly(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as client:
        await _register(client)
        project_id = await _create_project(client)
        source_id = await _upload_source(client, project_id)

        created = await client.post(
            f"/api/v1/projects/{project_id}/generations",
            json={"source_image_id": source_id, "prompt": "prueba"},
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert created.status_code == 202, created.text
        generation_id = created.json()["id"]

        # El archivo de origen desaparece antes de que el trabajador lo lea.
        async with context.session_factory() as session:
            image = await session.get(ProjectImage, UUID(source_id))
            assert image is not None
            await context.storage.delete(image.storage_key)

        assert await _build_worker(context).process_next() is True

        failed = await client.get(f"/api/v1/generations/{generation_id}")
        assert failed.status_code == 200
        body = failed.json()
        assert body["status"] == "failed"
        assert body["error_code"] == "source_missing"
        assert body["result_image_id"] is None

        project = await client.get(f"/api/v1/projects/{project_id}")
        assert project.json()["status"] == "ready"

        async with context.session_factory() as session:
            stored = await session.get(Generation, UUID(generation_id))
            assert stored is not None
            assert stored.status.value == "failed"


async def test_generation_rejects_unknown_project(context: ApiContext) -> None:
    async with AsyncClient(transport=context.transport, base_url="http://test") as client:
        await _register(client)
        response = await client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/generations",
            json={
                "source_image_id": "00000000-0000-0000-0000-000000000000",
                "prompt": "prueba",
            },
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert response.status_code == 404
