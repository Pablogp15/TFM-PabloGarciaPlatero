"""Trabajador CPU de guías; una tarea por proceso y cola persistida."""

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models.enums import GuideStatus
from app.models.guide import Guide, GuideStep, GuideStepPaint
from app.models.project import ProjectImage
from app.schemas.guide_generation import GeneratedGuide, VisualAnalysis
from app.services.rag_embeddings import LocalEmbeddings
from app.services.rag_model import OllamaGuideModel, RagModelError
from app.services.rag_retrieval import retrieve
from app.storage.base import ImageStorage
from app.storage.deps import get_image_storage

logger = logging.getLogger(__name__)


class GuideCancelledError(Exception):
    pass


class GuideWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        storage: ImageStorage,
        model: OllamaGuideModel,
        encoder: LocalEmbeddings,
    ) -> None:
        self.sessions = sessions
        self.settings = settings
        self.storage = storage
        self.model = model
        self.encoder = encoder

    async def stage(self, guide_id: UUID, stage: str) -> None:
        async with self.sessions() as session:
            guide = await session.get(Guide, guide_id)
            if guide is None or guide.cancel_requested or guide.status != GuideStatus.GENERATING:
                raise GuideCancelledError
            guide.stage = stage
            await session.commit()

    async def process_next(self) -> bool:
        async with self.sessions() as session:
            guide = await session.scalar(
                select(Guide)
                .where(
                    Guide.status == GuideStatus.PENDING,
                )
                .order_by(Guide.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if guide is None:
                return False
            guide.status = GuideStatus.GENERATING
            guide.started_at = datetime.now(UTC)
            guide_id = guide.id
            await session.commit()
        started = monotonic()
        try:
            async with asyncio.timeout(self.settings.guide_timeout_seconds):
                await self.process(guide_id)
        except GuideCancelledError:
            await self.fail(guide_id, "cancelled", "Generación cancelada")
        except TimeoutError:
            await self.fail(guide_id, "failed", "Se agotó el tiempo de generación")
        except Exception:
            logger.exception("Fallo de guía %s", guide_id)
            await self.fail(
                guide_id,
                "failed",
                "No se pudo generar una guía válida. Comprueba el servicio y el corpus.",
            )
        logger.info("Guía %s finalizada en %.1f segundos", guide_id, monotonic() - started)
        return True

    async def fail(self, guide_id: UUID, stage: str, message: str) -> None:
        async with self.sessions() as session:
            await session.execute(
                update(Guide)
                .where(
                    Guide.id == guide_id,
                    Guide.status == GuideStatus.GENERATING,
                )
                .values(
                    status=GuideStatus.FAILED,
                    stage=stage,
                    error_message=message,
                    finished_at=datetime.now(UTC),
                )
            )
            await session.commit()

    async def process(self, guide_id: UUID) -> None:
        started = monotonic()
        await self.stage(guide_id, "analysis")
        async with self.sessions() as session:
            guide = await session.get(Guide, guide_id)
            assert guide is not None
            context = dict(guide.context)
            image = await session.get(ProjectImage, guide.target_image_id)
            if image is None:
                raise ValueError("Imagen no disponible")
            image_key = image.storage_key
        image_bytes = await self.storage.read(image_key)
        analysis = await self.model.generate(
            VisualAnalysis,
            "Identifica las zonas visibles, materiales aparentes y colores de la miniatura. "
            "No inventes caras ocultas ni referencias comerciales. Explica las incertidumbres.",
            {"project": context.get("project"), "description": context.get("description")},
            image_bytes,
        )
        await self.stage(guide_id, "retrieval")
        query = "técnicas pintado miniaturas " + " ".join(
            f"{zone.name} {zone.material} {zone.color}" for zone in analysis.zones
        )
        vector = (await asyncio.to_thread(self.encoder.encode, [query], query=True))[0]
        async with self.sessions() as session:
            chunks = await retrieve(session, query, vector, self.settings.guide_embedding_revision)
            sources = [
                {
                    "id": str(chunk.id),
                    "title": chunk.title,
                    "content": chunk.content,
                    "metadata": chunk.doc_metadata,
                }
                for chunk in chunks
            ]
        if not sources:
            raise ValueError("Corpus sin fuentes recuperables")
        await self.stage(guide_id, "writing")
        request: dict[str, Any] = {
            **context,
            "analysis": analysis.model_dump(),
            "sources": [
                {"id": source["id"], "title": source["title"], "content": source["content"]}
                for source in sources
            ],
        }
        instruction = (
            "Redacta una guía de pintado de miniaturas clara y ordenada. Usa exclusivamente los "
            "paint_ids del inventario y source_ids de las fuentes recibidas. Cada paso necesita "
            "Fuentes que respalden su técnica. No inventes secados ni mezclas. "
            "No confundas tipos de pintura por similitud de color. Explica aproximaciones, "
            "incertidumbres y pasos imposibles; no exijas compras. El tiempo es una estimación. "
            "La lista inventory es la instantánea de pinturas disponibles aportada por el "
            "backend: úsala sin exigir confirmarla mediante la imagen. La identidad comercial "
            "del personaje no es necesaria. Convierte la revisión de montaje, limpieza o "
            "disponibilidad de herramientas en comprobaciones que realizará el usuario antes "
            "de continuar, sin afirmar que ya se han realizado. Estos pasos pueden tener "
            "paint_ids vacío. Si faltan colores para reproducir toda la imagen, ofrece los "
            "pasos viables con los colores disponibles y explica qué zonas no se pueden "
            "reproducir, sin asumir equivalencias de acabado ni inventar materiales. "
            "Propón como máximo seis pasos concretos. Usa other para preparación sin pintura, "
            "y paint_ids no vacío para toda técnica de pintado. No prescribas colores ausentes "
            "aunque aparezcan en la imagen: declara esas zonas como limitación. Cada cita debe "
            "contener la técnica concreta del paso, no solo comentarios sobre montaje. "
            "Si no puedes fundamentar pasos, devuelve steps vacío y explica las limitaciones."
        )
        output: GeneratedGuide | None = None
        for attempt in range(2):
            try:
                output = await self.model.generate(GeneratedGuide, instruction, request)
                output.validate_references(
                    {UUID(paint["id"]) for paint in context["inventory"]},
                    {UUID(str(source["id"])) for source in sources},
                )
                break
            except (ValueError, RagModelError) as exc:
                if attempt:
                    raise
                request["correction"] = (
                    "La respuesta anterior no cumplió el contrato. Revisa IDs y formato. "
                    + str(exc)[:500]
                )
                await self.stage(guide_id, "writing")
        assert output is not None
        await self.stage(guide_id, "validation")
        async with self.sessions() as session:
            guide = await session.scalar(
                select(Guide).where(Guide.id == guide_id).with_for_update()
            )
            if guide is None or guide.cancel_requested or guide.status != GuideStatus.GENERATING:
                raise GuideCancelledError
            guide.analysis = analysis.model_dump()
            guide.retrieved_chunks = sources
            guide.summary = output.summary
            guide.limitations = list(dict.fromkeys(analysis.limitations + output.limitations))
            guide.llm_model = self.settings.guide_model
            guide.metrics = {
                "duration_seconds": round(monotonic() - started, 2),
                "device": "cpu",
                "embedding_revision": self.settings.guide_embedding_revision,
            }
            for position, item in enumerate(output.steps, 1):
                step = GuideStep(
                    guide_id=guide_id,
                    position=position,
                    title=item.title,
                    zone=item.zone,
                    objective=item.objective,
                    technique=item.technique,
                    description=item.description,
                    continue_when=item.continue_when,
                    time_minutes=item.time_minutes,
                    is_optional=item.is_optional,
                    source_ids=[str(key) for key in item.source_ids],
                )
                step.paints = [GuideStepPaint(paint_id=key) for key in item.paint_ids]
                session.add(step)
            guide.total_minutes = sum(step.time_minutes or 0 for step in output.steps)
            guide.status = GuideStatus.READY
            guide.stage = "done"
            guide.finished_at = datetime.now(UTC)
            await session.commit()

    async def run(self) -> None:
        while True:
            async with self.sessions() as session:
                await session.execute(
                    update(Guide)
                    .where(
                        Guide.status == GuideStatus.GENERATING,
                        Guide.started_at
                        < datetime.now(UTC)
                        - timedelta(seconds=self.settings.guide_timeout_seconds + 120),
                    )
                    .values(
                        status=GuideStatus.FAILED,
                        stage="failed",
                        error_message="Trabajo interrumpido; vuelve a generar la guía",
                        finished_at=datetime.now(UTC),
                    )
                )
                await session.commit()
            if not await self.process_next():
                await asyncio.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    settings = get_settings()
    encoder = LocalEmbeddings(settings.guide_embedding_path)
    worker = GuideWorker(
        get_session_factory(),
        settings,
        get_image_storage(),
        OllamaGuideModel(
            settings.guide_ollama_url, settings.guide_model, settings.guide_timeout_seconds
        ),
        encoder,
    )
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
