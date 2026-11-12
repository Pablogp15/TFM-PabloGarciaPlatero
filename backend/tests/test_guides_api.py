"""Privacidad, admisión y seguimiento de guías sobre PostgreSQL de pruebas."""

import json
import os
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_catalog_inventory_api import _csrf, _register, transport  # noqa: F401

from app.core.config import get_settings
from app.guide_worker import GuideWorker
from app.models.enums import GuideStatus, KnowledgeCategory, TechniqueType
from app.models.guide import Guide, GuideStep, GuideStepPaint
from app.models.knowledge import KnowledgeDocument
from app.models.project import ProjectImage
from app.services.rag_embeddings import LocalEmbeddings
from app.services.rag_model import OllamaGuideModel
from app.services.rag_retrieval import retrieve
from app.storage.local import LocalImageStorage

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Requiere PostgreSQL"
)


async def test_guides_flow(transport: ASGITransport) -> None:  # noqa: F811
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as owner:
            await _register(owner)
            headers = {"X-CSRF-Token": _csrf(owner)}
            project = (
                await owner.post("/api/v1/projects", json={"name": "Guía"}, headers=headers)
            ).json()
            project_id = project["id"]
            endpoint = f"/api/v1/projects/{project_id}/guides"
            assert (await owner.get(endpoint)).json()["corpus_ready"] is False
            async with sessions() as session:
                image = ProjectImage(
                    project_id=UUID(project_id),
                    kind="source",
                    storage_key="test.png",
                    mime_type="image/png",
                    width=512,
                    height=512,
                    size_bytes=5,
                    checksum="f" * 64,
                )
                session.add(image)
                await session.commit()
                image_id = str(image.id)
            assert (await owner.post(endpoint, json={"image_id": image_id})).status_code == 403
            assert (
                await owner.post(endpoint, json={"image_id": image_id}, headers=headers)
            ).status_code == 409
            async with sessions() as session:
                source = KnowledgeDocument(
                    document_key="test",
                    chunk_index=0,
                    title="Prueba",
                    category=KnowledgeCategory.TECHNIQUE,
                    content="Capa base de pintura",
                    embedding=[1.0] + [0.0] * 383,
                    doc_metadata={
                        "active": True,
                        "synthetic": True,
                        "embedding_revision": "local-v1",
                    },
                )
                session.add(source)
                await session.commit()
                source_id = source.id
            assert (await owner.get(endpoint)).json()["corpus_ready"] is False
            async with sessions() as session:
                source = await session.get(KnowledgeDocument, source_id)
                assert source is not None
                source.doc_metadata = {**source.doc_metadata, "synthetic": False}
                await session.commit()
                found = await retrieve(session, "pintura", [1.0] + [0.0] * 383, "local-v1")
                assert [item.id for item in found] == [source_id]
            assert (await owner.get(endpoint)).json()["corpus_ready"] is True
            assert (
                await owner.post(endpoint, json={"image_id": image_id}, headers=headers)
            ).status_code == 409
            paint = (await owner.get("/api/v1/paints?limit=1")).json()["items"][0]
            inventory = (
                await owner.post(
                    "/api/v1/inventory",
                    json={"paint_id": paint["id"], "running_low": True},
                    headers=headers,
                )
            ).json()
            created = await owner.post(endpoint, json={"image_id": image_id}, headers=headers)
            assert created.status_code == 202
            guide_id = created.json()["id"]
            assert created.json()["context"]["inventory"][0]["running_low"] is True
            assert (
                await owner.post(endpoint, json={"image_id": image_id}, headers=headers)
            ).status_code == 409
            async with AsyncClient(transport=transport, base_url="http://test") as other:
                await _register(other, "other@example.com")
                assert (await other.get(endpoint)).status_code == 404
                assert (
                    await other.post(
                        f"{endpoint}/{guide_id}/cancel", headers={"X-CSRF-Token": _csrf(other)}
                    )
                ).status_code == 404
            async with sessions() as session:
                guide = await session.get(Guide, UUID(guide_id))
                assert guide is not None
                guide.status = GuideStatus.READY
                guide.stage = "done"
                step = GuideStep(
                    guide_id=guide.id,
                    position=1,
                    title="Base",
                    technique=TechniqueType.BASE_COAT,
                    description="Prueba",
                    source_ids=[str(source_id)],
                )
                step.paints = [GuideStepPaint(paint_id=UUID(paint["id"]))]
                session.add(step)
                await session.commit()
                step_id = str(step.id)
            progress_url = f"{endpoint}/{guide_id}/steps/{step_id}/progress"
            response = await owner.put(
                progress_url,
                json={"completed": True, "note": "Listo", "minutes_spent": 12},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["steps"][0]["completed"] is True
            assert (await owner.get(f"{endpoint}/{guide_id}")).json()["steps"][0][
                "minutes_spent"
            ] == 12
            await owner.patch(
                f"/api/v1/inventory/{inventory['id']}", json={"quantity": 0}, headers=headers
            )
            assert (await owner.get(f"{endpoint}/{guide_id}")).json()["unavailable_paint_ids"] == [
                paint["id"]
            ]
            assert (
                await owner.put(
                    progress_url, json={"completed": True, "minutes_spent": -1}, headers=headers
                )
            ).status_code == 422
            async with sessions() as session:
                count = len(list((await session.scalars(select(GuideStep))).all()))
                assert count == 1
    finally:
        await engine.dispose()


@pytest.mark.parametrize("cancel_during_analysis", [False, True])
async def test_worker_publishes_only_valid_uncancelled_results(
    transport: ASGITransport,
    tmp_path: Path,
    cancel_during_analysis: bool,
) -> None:
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalImageStorage(tmp_path)
    await storage.save("input.png", b"synthetic")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register(client)
        headers = {"X-CSRF-Token": _csrf(client)}
        project = (
            await client.post("/api/v1/projects", json={"name": "Worker"}, headers=headers)
        ).json()
        paint = (await client.get("/api/v1/paints?limit=1")).json()["items"][0]
        async with sessions() as session:
            image = ProjectImage(
                project_id=UUID(project["id"]),
                kind="source",
                storage_key="input.png",
                mime_type="image/png",
                width=512,
                height=512,
                size_bytes=9,
                checksum="a" * 64,
            )
            source = KnowledgeDocument(
                document_key="worker",
                chunk_index=0,
                title="Prueba",
                category=KnowledgeCategory.TECHNIQUE,
                content="Capa base de pintura",
                embedding=[1.0] + [0.0] * 383,
                doc_metadata={"active": True, "synthetic": False, "embedding_revision": "local-v1"},
            )
            session.add_all([image, source])
            await session.flush()
            guide = Guide(
                project_id=UUID(project["id"]),
                target_image_id=image.id,
                context={"inventory": [{"id": paint["id"], "name": paint["name"]}]},
            )
            session.add(guide)
            await session.commit()
            guide_id, source_id = guide.id, source.id

        class Encoder(LocalEmbeddings):
            def __init__(self) -> None:
                pass

            def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
                return [[1.0] + [0.0] * 383]

        async def response(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            if "images" in payload["messages"][1]:
                if cancel_during_analysis:
                    async with sessions() as session:
                        current = await session.get(Guide, guide_id)
                        assert current is not None
                        current.cancel_requested = True
                        await session.commit()
                value = {
                    "zones": [{"name": "capa", "material": "tela", "color": "negro"}],
                    "limitations": [],
                }
            else:
                value = {
                    "summary": "Prueba",
                    "limitations": [],
                    "steps": [
                        {
                            "title": "Base",
                            "zone": "capa",
                            "objective": "Cubrir",
                            "technique": "base_coat",
                            "description": "Aplicar pintura",
                            "continue_when": "Cobertura uniforme",
                            "paint_ids": [paint["id"]],
                            "source_ids": [str(source_id)],
                        }
                    ],
                }
            return httpx.Response(200, json={"message": {"content": json.dumps(value)}})

        worker = GuideWorker(
            sessions,
            get_settings(),
            storage,
            OllamaGuideModel("http://test", "test", transport=httpx.MockTransport(response)),
            Encoder(),
        )
        assert await worker.process_next()
        async with sessions() as session:
            final = await session.get(Guide, guide_id)
            assert final is not None
            assert final.stage == ("cancelled" if cancel_during_analysis else "done")
            steps = list(
                (
                    await session.scalars(select(GuideStep).where(GuideStep.guide_id == guide_id))
                ).all()
            )
            assert len(steps) == (0 if cancel_during_analysis else 1)
    await engine.dispose()
