"""Trabajador que procesa la cola de generaciones."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models.enums import GenerationStage, GenerationStatus, ImageKind
from app.models.generation import Generation
from app.models.project import ProjectImage
from app.services.generation_queue import GenerationQueue
from app.services.generator import (
    GenerationCancelledError,
    GenerationError,
    GenerationRequest,
    GenerationResult,
    ImageGenerator,
    ProgressCallback,
    build_generator,
)
from app.services.image_validation import (
    ImageValidationError,
    ImageValidator,
    ValidatedImage,
)
from app.storage.base import ImageStorage, StorageObjectNotFoundError
from app.storage.deps import get_image_storage

logger = logging.getLogger(__name__)

_SessionFactory = async_sessionmaker[AsyncSession]


@dataclass(frozen=True, slots=True)
class _JobContext:
    generation_id: UUID
    project_id: UUID
    source_key: str
    prompt: str
    negative_prompt: str | None
    num_inference_steps: int
    width: int
    height: int
    seed: int | None


class GenerationWorker:
    """Reclama y ejecuta trabajos de uno en uno.

    La concurrencia es deliberadamente 1: el modelo ocupa casi toda la VRAM de
    una GPU de 8 GB, así que dos inferencias simultáneas provocarían OOM.
    """

    def __init__(
        self,
        session_factory: _SessionFactory,
        storage: ImageStorage,
        validator: ImageValidator,
        generator: ImageGenerator,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage
        self._validator = validator
        self._generator = generator
        self._settings = settings

    async def run_forever(self) -> None:
        """Recupera trabajos huérfanos y atiende la cola indefinidamente."""
        await self.recover_stale()
        logger.info("Trabajador de generación iniciado (%s)", self._generator.provider)

        while True:
            processed = await self.process_next()
            if not processed:
                await asyncio.sleep(self._settings.generation_worker_poll_seconds)

    async def recover_stale(self) -> None:
        margin = self._settings.generation_job_timeout_seconds + 120
        async with self._session_factory() as session:
            recovered = await GenerationQueue(session).recover_stale(
                timedelta(seconds=margin)
            )
        if recovered:
            logger.warning("Se marcaron %s generaciones huérfanas como fallidas", recovered)

    async def process_next(self) -> bool:
        """Procesa un trabajo si hay alguno disponible."""
        async with self._session_factory() as session:
            generation_id = await GenerationQueue(session).claim_next()
        if generation_id is None:
            return False

        try:
            await self._process(generation_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Un fallo inesperado nunca debe detener el bucle del trabajador.
            logger.exception("Error no controlado al procesar la generación %s", generation_id)
            await self._fail(
                generation_id,
                "worker_error",
                "Error interno al procesar la generación",
            )
        return True

    async def _process(self, generation_id: UUID) -> None:
        context = await self._load_context(generation_id)
        if context is None:
            return

        try:
            source_image = await self._storage.read(context.source_key)
        except StorageObjectNotFoundError:
            await self._fail(
                generation_id,
                "source_missing",
                "La imagen de origen ya no está disponible",
            )
            return

        request = GenerationRequest(
            source_image=source_image,
            prompt=context.prompt,
            negative_prompt=context.negative_prompt,
            num_inference_steps=context.num_inference_steps,
            width=context.width,
            height=context.height,
            seed=context.seed,
        )

        try:
            result = await self._generator.generate(
                request,
                on_progress=self._progress_writer(generation_id),
                should_cancel=lambda: self._cancel_requested(generation_id),
            )
        except GenerationCancelledError:
            async with self._session_factory() as session:
                await GenerationQueue(session).mark_cancelled(generation_id)
            return
        except GenerationError as exc:
            await self._fail(generation_id, exc.code, exc.message)
            return

        await self._store_result(context, result)

    async def _load_context(self, generation_id: UUID) -> _JobContext | None:
        async with self._session_factory() as session:
            generation = await session.get(Generation, generation_id)
            if generation is None or generation.status is not GenerationStatus.RUNNING:
                return None

            source = await session.get(ProjectImage, generation.source_image_id)
            if source is None:
                await GenerationQueue(session).mark_failed(
                    generation_id,
                    error_code="source_missing",
                    error_message="La imagen de origen ya no está disponible",
                )
                return None

            params = generation.params or {}
            return _JobContext(
                generation_id=generation.id,
                project_id=generation.project_id,
                source_key=source.storage_key,
                prompt=generation.prompt,
                negative_prompt=generation.negative_prompt,
                num_inference_steps=_int_param(params, "num_inference_steps", 20),
                width=_int_param(params, "width", 768),
                height=_int_param(params, "height", 768),
                seed=_optional_int_param(params, "seed"),
            )

    def _progress_writer(self, generation_id: UUID) -> ProgressCallback:
        last_stage: GenerationStage | None = None
        last_percent = -100
        last_write = 0.0

        async def on_progress(stage: GenerationStage, percent: int) -> None:
            nonlocal last_stage, last_percent, last_write

            now = monotonic()
            if (
                stage is last_stage
                and percent - last_percent < 5
                and now - last_write < 2.0
            ):
                return

            last_stage = stage
            last_percent = percent
            last_write = now
            async with self._session_factory() as session:
                await GenerationQueue(session).update_progress(
                    generation_id, stage, percent
                )

        return on_progress

    async def _cancel_requested(self, generation_id: UUID) -> bool:
        async with self._session_factory() as session:
            status = await session.scalar(
                select(Generation.status).where(Generation.id == generation_id)
            )
        return status is not GenerationStatus.RUNNING

    async def _store_result(
        self,
        context: _JobContext,
        result: GenerationResult,
    ) -> None:
        try:
            validated = await self._validator.validate(result.data)
        except ImageValidationError:
            await self._fail(
                context.generation_id,
                "invalid_output",
                "La imagen generada no supera la validación",
            )
            return

        if validated.size_bytes > self._settings.generation_max_output_bytes:
            await self._fail(
                context.generation_id,
                "invalid_output",
                "La imagen generada supera el tamaño máximo permitido",
            )
            return

        storage_key = f"projects/{context.project_id}/{uuid4().hex}.{validated.extension}"
        await self._storage.save(storage_key, validated.data)

        try:
            created, succeeded = await self._persist_result(
                context,
                result,
                validated,
                storage_key,
            )
            if not succeeded or not created:
                # Si se canceló durante el guardado, o el contenido ya existía,
                # el archivo recién escrito es redundante.
                await self._delete_quietly(storage_key)
        except Exception:
            await self._delete_quietly(storage_key)
            raise

    async def _persist_result(
        self,
        context: _JobContext,
        result: GenerationResult,
        validated: ValidatedImage,
        storage_key: str,
    ) -> tuple[bool, bool]:
        """Inserta la imagen y cierra el trabajo en la misma transacción.

        Devuelve ``(creada, confirmada)``. ``confirmada`` es falso si el usuario
        canceló entre la reclamación y el guardado; en ese caso la transacción
        se revierte y no queda ninguna imagen huérfana.
        """
        async with self._session_factory() as session:
            existing = await self._find_by_checksum(
                session, context.project_id, validated.checksum
            )
            created = existing is None
            image_id: UUID | None = None
            if existing is None:
                image = ProjectImage(
                    project_id=context.project_id,
                    kind=ImageKind.GENERATED,
                    storage_key=storage_key,
                    mime_type=validated.mime_type,
                    width=validated.width,
                    height=validated.height,
                    size_bytes=validated.size_bytes,
                    checksum=validated.checksum,
                )
                session.add(image)
                try:
                    await session.flush()
                except IntegrityError:
                    # Otra petición guardó el mismo contenido a la vez.
                    await session.rollback()
                    existing = await self._find_by_checksum(
                        session, context.project_id, validated.checksum
                    )
                    if existing is None:
                        raise
                    created = False
                else:
                    image_id = image.id
            if existing is not None:
                image_id = existing.id

            if image_id is None:
                raise RuntimeError("No se pudo resolver la imagen generada")

            succeeded = await GenerationQueue(session).mark_succeeded(
                context.generation_id,
                result_image_id=image_id,
                provider=result.provider,
                model_name=result.model_name,
                job_id=result.job_id,
                model_load_ms=result.model_load_ms,
                inference_ms=result.inference_ms,
                vram_peak_mb=result.vram_peak_mb,
            )
            return created, succeeded

    async def _find_by_checksum(
        self,
        session: AsyncSession,
        project_id: UUID,
        checksum: str,
    ) -> ProjectImage | None:
        return await session.scalar(
            select(ProjectImage).where(
                ProjectImage.project_id == project_id,
                ProjectImage.checksum == checksum,
            )
        )

    async def _fail(self, generation_id: UUID, code: str, message: str) -> None:
        async with self._session_factory() as session:
            await GenerationQueue(session).mark_failed(
                generation_id,
                error_code=code,
                error_message=message,
            )

    async def _delete_quietly(self, storage_key: str) -> None:
        try:
            await self._storage.delete(storage_key)
        except Exception:
            logger.warning(
                "No se pudo eliminar el archivo huérfano %s",
                storage_key,
                exc_info=True,
            )


def _int_param(params: dict[str, Any], name: str, default: int) -> int:
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _optional_int_param(params: dict[str, Any], name: str) -> int | None:
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def build_worker(settings: Settings | None = None) -> GenerationWorker:
    """Construye el trabajador con las dependencias reales de la aplicación."""
    resolved = settings or get_settings()
    return GenerationWorker(
        session_factory=get_session_factory(),
        storage=get_image_storage(),
        validator=ImageValidator(
            max_bytes=resolved.generation_max_output_bytes,
            max_pixels=resolved.max_image_pixels,
            max_dimension=resolved.max_image_dimension,
        ),
        generator=build_generator(resolved),
        settings=resolved,
    )
