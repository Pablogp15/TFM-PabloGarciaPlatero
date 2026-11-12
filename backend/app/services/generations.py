"""Casos de uso de las generaciones: alta, consulta y cancelación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import (
    GenerationStatus,
    ImageKind,
    QualityMode,
)
from app.models.generation import Generation
from app.models.project import Project, ProjectImage
from app.schemas.generation import GenerationCreate
from app.services.generation_queue import GenerationQueue
from app.services.projects import ProjectService


class GenerationNotFoundError(Exception):
    """La generación no existe o pertenece a otro usuario."""


class InvalidSourceImageError(Exception):
    """La imagen indicada no pertenece al proyecto o no es de origen."""


class GenerationLimitError(Exception):
    """El proyecto ya tiene una generación activa."""


class GenerationQuotaError(Exception):
    """El proyecto alcanzó su cuota total de generaciones."""


class GenerationNotCancellableError(Exception):
    """La generación ya terminó y no se puede cancelar."""


@dataclass(frozen=True, slots=True)
class ResolvedParams:
    num_inference_steps: int
    width: int
    height: int
    seed: int | None

    def as_dict(self) -> dict[str, int | None]:
        return {
            "num_inference_steps": self.num_inference_steps,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
        }


# Presets acordados con el servicio GPU. Un valor explícito siempre gana.
_QUALITY_PRESETS: dict[QualityMode, tuple[int, int, int]] = {
    QualityMode.DRAFT: (20, 768, 768),
    QualityMode.FINAL: (30, 1024, 1024),
}

_ESTIMATED_SECONDS: dict[QualityMode, int] = {
    QualityMode.DRAFT: 180,
    QualityMode.FINAL: 300,
}


def resolve_params(payload: GenerationCreate) -> ResolvedParams:
    """Combina el preset de calidad con los valores explícitos del usuario."""
    steps, width, height = _QUALITY_PRESETS[payload.quality]
    return ResolvedParams(
        num_inference_steps=payload.num_inference_steps or steps,
        width=payload.width or width,
        height=payload.height or height,
        seed=payload.seed,
    )


class GenerationService:
    """Toda consulta se acota al usuario autenticado."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def create(
        self,
        user_id: UUID,
        project_id: UUID,
        payload: GenerationCreate,
    ) -> Generation:
        project = await ProjectService(self._session).get_owned(user_id, project_id)

        source = await self._session.scalar(
            select(ProjectImage).where(
                ProjectImage.id == payload.source_image_id,
                ProjectImage.project_id == project.id,
            )
        )
        if source is None or source.kind is not ImageKind.SOURCE:
            raise InvalidSourceImageError

        await self._check_limits(user_id, project.id)

        params = resolve_params(payload)
        provider = "qwen-local" if self._settings.generation_provider == "http" else "stub"
        generation = Generation(
            project_id=project.id,
            source_image_id=source.id,
            provider=provider,
            model_name=self._settings.generation_model_name,
            quality=payload.quality,
            prompt=payload.prompt,
            negative_prompt=payload.negative_prompt,
            params={
                **params.as_dict(),
                "quality": payload.quality.value,
            },
            status=GenerationStatus.QUEUED,
            estimated_seconds=_ESTIMATED_SECONDS[payload.quality],
        )
        self._session.add(generation)
        project.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(generation)
        return generation

    async def list_generations(
        self,
        user_id: UUID,
        project_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Generation], int]:
        await ProjectService(self._session).get_owned(user_id, project_id)

        total = await self._session.scalar(
            select(func.count()).select_from(Generation).where(Generation.project_id == project_id)
        )

        statement = (
            select(Generation)
            .where(Generation.project_id == project_id)
            .order_by(Generation.created_at.desc(), Generation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return items, int(total or 0)

    async def get_owned(self, user_id: UUID, generation_id: UUID) -> Generation:
        generation = await self._session.scalar(
            select(Generation)
            .join(Project, Generation.project_id == Project.id)
            .where(Generation.id == generation_id, Project.user_id == user_id)
        )
        if generation is None:
            raise GenerationNotFoundError
        return generation

    async def cancel(self, user_id: UUID, generation_id: UUID) -> Generation:
        generation = await self.get_owned(user_id, generation_id)
        if generation.status not in (GenerationStatus.QUEUED, GenerationStatus.RUNNING):
            raise GenerationNotCancellableError

        project_id = await self._session.scalar(
            update(Generation)
            .where(
                Generation.id == generation_id,
                Generation.status.in_((GenerationStatus.QUEUED, GenerationStatus.RUNNING)),
            )
            .values(
                status=GenerationStatus.CANCELLED,
                finished_at=datetime.now(UTC),
            )
            .returning(Generation.project_id)
        )
        if project_id is None:
            await self._session.rollback()
            raise GenerationNotCancellableError

        await GenerationQueue(self._session).sync_project_status(project_id)
        await self._session.commit()
        await self._session.refresh(generation)
        return generation

    async def _check_limits(self, user_id: UUID, project_id: UUID) -> None:
        active = await self._session.scalar(
            select(func.count())
            .select_from(Generation)
            .where(
                Generation.project_id == project_id,
                Generation.status.in_((GenerationStatus.QUEUED, GenerationStatus.RUNNING)),
            )
        )
        if int(active or 0) >= self._settings.generation_max_active_per_project:
            raise GenerationLimitError

        total = await self._session.scalar(
            select(func.count()).select_from(Generation).where(Generation.project_id == project_id)
        )
        if int(total or 0) >= self._settings.generation_max_per_project:
            raise GenerationQuotaError
