"""Operaciones de cola sobre la tabla ``generations``.

La propia base de datos actúa como cola: no se añade un broker externo. El
trabajador reclama el trabajo más antiguo con ``FOR UPDATE SKIP LOCKED``, de
modo que varios trabajadores podrían convivir sin entregar dos veces el mismo
trabajo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GenerationStage, GenerationStatus, ProjectStatus
from app.models.generation import Generation
from app.models.project import Project


class GenerationQueue:
    """Transiciones de estado del trabajador, siempre condicionadas."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_next(self) -> UUID | None:
        """Reclama un trabajo en cola y lo pasa a ``running``."""
        generation = await self._session.scalar(
            select(Generation)
            .where(Generation.status == GenerationStatus.QUEUED)
            .order_by(Generation.queued_at, Generation.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if generation is None:
            return None

        now = datetime.now(UTC)
        generation.status = GenerationStatus.RUNNING
        generation.progress_stage = GenerationStage.LOADING
        generation.progress_percent = 0
        generation.started_at = now

        project = await self._session.get(Project, generation.project_id)
        if project is not None and project.status not in (
            ProjectStatus.COMPLETED,
            ProjectStatus.ARCHIVED,
        ):
            project.status = ProjectStatus.GENERATING
            project.updated_at = now

        await self._session.commit()
        return generation.id

    async def update_progress(
        self,
        generation_id: UUID,
        stage: GenerationStage,
        percent: int,
    ) -> bool:
        """Actualiza el progreso solo si el trabajo sigue en ejecución."""
        updated = await self._session.scalar(
            update(Generation)
            .where(
                Generation.id == generation_id,
                Generation.status == GenerationStatus.RUNNING,
            )
            .values(progress_stage=stage, progress_percent=max(0, min(100, percent)))
            .returning(Generation.id)
        )
        await self._session.commit()
        return updated is not None

    async def mark_succeeded(
        self,
        generation_id: UUID,
        *,
        result_image_id: UUID,
        provider: str,
        model_name: str,
        job_id: str,
        model_load_ms: int,
        inference_ms: int,
        vram_peak_mb: int,
    ) -> bool:
        """Cierra el trabajo con éxito. Falla si ya no estaba en ejecución."""
        project_id = await self._session.scalar(
            update(Generation)
            .where(
                Generation.id == generation_id,
                Generation.status == GenerationStatus.RUNNING,
            )
            .values(
                status=GenerationStatus.SUCCEEDED,
                progress_stage=GenerationStage.DONE,
                progress_percent=100,
                result_image_id=result_image_id,
                provider=provider,
                model_name=model_name,
                job_id=job_id,
                model_load_ms=model_load_ms,
                inference_ms=inference_ms,
                vram_peak_mb=vram_peak_mb,
                finished_at=datetime.now(UTC),
                error_code=None,
                error_message=None,
            )
            .returning(Generation.project_id)
        )
        if project_id is None:
            await self._session.rollback()
            return False

        await self.sync_project_status(project_id)
        await self._session.commit()
        return True

    async def mark_failed(
        self,
        generation_id: UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        """Cierra el trabajo con error sin sobrescribir una cancelación."""
        project_id = await self._session.scalar(
            update(Generation)
            .where(
                Generation.id == generation_id,
                Generation.status == GenerationStatus.RUNNING,
            )
            .values(
                status=GenerationStatus.FAILED,
                error_code=error_code[:60],
                error_message=error_message[:1000],
                finished_at=datetime.now(UTC),
            )
            .returning(Generation.project_id)
        )
        if project_id is None:
            await self._session.rollback()
            return False

        await self.sync_project_status(project_id)
        await self._session.commit()
        return True

    async def mark_cancelled(self, generation_id: UUID) -> bool:
        """Confirma una cancelación pedida por el usuario o por el trabajador."""
        project_id = await self._session.scalar(
            update(Generation)
            .where(
                Generation.id == generation_id,
                Generation.status == GenerationStatus.RUNNING,
            )
            .values(
                status=GenerationStatus.CANCELLED,
                finished_at=datetime.now(UTC),
            )
            .returning(Generation.project_id)
        )
        if project_id is None:
            await self._session.rollback()
            return False

        await self.sync_project_status(project_id)
        await self._session.commit()
        return True

    async def recover_stale(self, older_than: timedelta) -> int:
        """Marca como fallidos los trabajos que quedaron huérfanos.

        Ocurre si el proceso del trabajador muere mientras una generación está
        en ejecución: sin esta recuperación el proyecto quedaría atascado en
        ``generating`` para siempre.
        """
        cutoff = datetime.now(UTC) - older_than
        project_ids = list(
            (
                await self._session.scalars(
                    update(Generation)
                    .where(
                        Generation.status == GenerationStatus.RUNNING,
                        Generation.started_at < cutoff,
                    )
                    .values(
                        status=GenerationStatus.FAILED,
                        error_code="worker_lost",
                        error_message="El trabajador se detuvo durante la generación",
                        finished_at=datetime.now(UTC),
                    )
                    .returning(Generation.project_id)
                )
            ).all()
        )
        for project_id in set(project_ids):
            await self.sync_project_status(project_id)
        await self._session.commit()
        return len(project_ids)

    async def sync_project_status(self, project_id: UUID) -> None:
        """Devuelve el proyecto a ``ready`` cuando ya no quedan trabajos activos."""
        project = await self._session.get(Project, project_id)
        if project is None or project.status is not ProjectStatus.GENERATING:
            return

        active = await self._session.scalar(
            select(func.count())
            .select_from(Generation)
            .where(
                Generation.project_id == project_id,
                Generation.status.in_((GenerationStatus.QUEUED, GenerationStatus.RUNNING)),
            )
        )
        if int(active or 0) == 0:
            project.status = ProjectStatus.READY
            project.updated_at = datetime.now(UTC)
