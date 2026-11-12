"""Guías privadas, instantánea del inventario y seguimiento persistente."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import GuideStatus
from app.models.guide import Guide, GuideStep
from app.models.knowledge import KnowledgeDocument
from app.models.paint import UserPaint
from app.models.progress import ProgressEntry
from app.models.project import Project, ProjectImage
from app.schemas.guide import GuideList, GuideProgress, GuideRead, GuideStepRead


class GuideError(Exception):
    def __init__(self, detail: str, status: int = 409) -> None:
        self.detail = detail
        self.status = status


class GuideService:
    def __init__(self, session: AsyncSession, revision: str) -> None:
        self.session = session
        self.revision = revision

    async def project(self, user_id: UUID, project_id: UUID, lock: bool = False) -> Project:
        query = select(Project).where(Project.id == project_id, Project.user_id == user_id)
        if lock:
            query = query.with_for_update()
        project = await self.session.scalar(query)
        if project is None:
            raise GuideError("Proyecto no encontrado", 404)
        return project

    async def corpus_ready(self) -> bool:
        return bool(
            await self.session.scalar(
                select(KnowledgeDocument.id)
                .where(
                    KnowledgeDocument.embedding.is_not(None),
                    KnowledgeDocument.doc_metadata["synthetic"].astext == "false",
                    KnowledgeDocument.doc_metadata["active"].astext == "true",
                    KnowledgeDocument.doc_metadata["embedding_revision"].astext == self.revision,
                )
                .limit(1)
            )
        )

    async def create(self, user_id: UUID, project_id: UUID, image_id: UUID) -> GuideRead:
        project = await self.project(user_id, project_id, lock=True)
        if not await self.corpus_ready():
            raise GuideError("Importa documentos para las guías.")
        image = await self.session.scalar(
            select(ProjectImage).where(
                ProjectImage.id == image_id,
                ProjectImage.project_id == project_id,
            )
        )
        if image is None:
            raise GuideError("Imagen no encontrada en el proyecto", 404)
        active = await self.session.scalar(
            select(Guide.id)
            .where(
                Guide.project_id == project_id,
                Guide.status.in_([GuideStatus.PENDING, GuideStatus.GENERATING]),
            )
            .limit(1)
        )
        if active:
            raise GuideError("Ya hay una guía en proceso")
        count = await self.session.scalar(
            select(func.count()).select_from(Guide).where(Guide.project_id == project_id)
        )
        if (count or 0) >= 100:
            raise GuideError("Se ha alcanzado el límite de guías del proyecto")
        owned = list(
            (
                await self.session.scalars(
                    select(UserPaint)
                    .where(
                        UserPaint.user_id == user_id,
                        UserPaint.quantity > 0,
                    )
                    .options(selectinload(UserPaint.paint))
                )
            ).all()
        )
        if not owned:
            raise GuideError(
                "Añade al inventario pinturas con cantidad disponible antes de generar una guía."
            )
        inventory = [
            {
                "id": str(item.paint_id),
                "name": item.paint.name,
                "brand": item.paint.brand,
                "hex": item.paint.hex,
                "paint_type": item.paint.paint_type.value,
                "finish": item.paint.finish.value,
                "quantity": item.quantity,
                "running_low": item.running_low,
            }
            for item in owned
        ]
        guide = Guide(
            project_id=project_id,
            target_image_id=image_id,
            status=GuideStatus.PENDING,
            context={
                "project": project.name,
                "description": project.description,
                "inventory": inventory,
                "embedding_revision": self.revision,
            },
        )
        self.session.add(guide)
        await self.session.commit()
        return await self.read(user_id, project_id, guide.id)

    async def get(self, user_id: UUID, project_id: UUID, guide_id: UUID) -> Guide:
        await self.project(user_id, project_id)
        guide = await self.session.scalar(
            select(Guide)
            .where(
                Guide.id == guide_id,
                Guide.project_id == project_id,
            )
            .options(selectinload(Guide.steps).selectinload(GuideStep.paints))
        )
        if guide is None:
            raise GuideError("Guía no encontrada", 404)
        return guide

    async def read(self, user_id: UUID, project_id: UUID, guide_id: UUID) -> GuideRead:
        guide = await self.get(user_id, project_id, guide_id)
        available = set(
            (
                await self.session.scalars(
                    select(UserPaint.paint_id).where(
                        UserPaint.user_id == user_id, UserPaint.quantity > 0
                    )
                )
            ).all()
        )
        used = {paint.paint_id for step in guide.steps for paint in step.paints}
        return GuideRead(
            id=guide.id,
            project_id=project_id,
            target_image_id=guide.target_image_id,
            status=guide.status,
            stage=guide.stage,
            summary=guide.summary,
            limitations=guide.limitations,
            error_message=guide.error_message,
            cancel_requested=guide.cancel_requested,
            context=guide.context,
            sources=guide.retrieved_chunks,
            unavailable_paint_ids=list(used - available),
            created_at=guide.created_at,
            steps=[
                GuideStepRead(
                    id=step.id,
                    position=step.position,
                    title=step.title,
                    zone=step.zone,
                    objective=step.objective,
                    technique=step.technique.value,
                    description=step.description,
                    continue_when=step.continue_when,
                    source_ids=step.source_ids,
                    paint_ids=[p.paint_id for p in step.paints],
                    time_minutes=step.time_minutes,
                    is_optional=step.is_optional,
                    completed=step.completed,
                    progress_note=step.progress_note,
                    minutes_spent=step.minutes_spent,
                )
                for step in sorted(guide.steps, key=lambda step: step.position)
            ],
        )

    async def list(self, user_id: UUID, project_id: UUID) -> GuideList:
        await self.project(user_id, project_id)
        ids = list(
            (
                await self.session.scalars(
                    select(Guide.id)
                    .where(Guide.project_id == project_id)
                    .order_by(Guide.created_at.desc())
                    .limit(100)
                )
            ).all()
        )
        return GuideList(
            items=[await self.read(user_id, project_id, key) for key in ids],
            corpus_ready=await self.corpus_ready(),
        )

    async def cancel(self, user_id: UUID, project_id: UUID, guide_id: UUID) -> GuideRead:
        await self.project(user_id, project_id)
        guide = await self.session.scalar(
            select(Guide)
            .where(
                Guide.id == guide_id,
                Guide.project_id == project_id,
            )
            .with_for_update()
        )
        if guide is None:
            raise GuideError("Guía no encontrada", 404)
        if guide.status in (GuideStatus.PENDING, GuideStatus.GENERATING):
            guide.cancel_requested = True
            if guide.status == GuideStatus.PENDING:
                guide.status = GuideStatus.FAILED
                guide.stage = "cancelled"
                guide.finished_at = datetime.now(UTC)
            await self.session.commit()
        return await self.read(user_id, project_id, guide_id)

    async def progress(
        self, user_id: UUID, project_id: UUID, guide_id: UUID, step_id: UUID, payload: GuideProgress
    ) -> GuideRead:
        guide = await self.get(user_id, project_id, guide_id)
        if guide.status != GuideStatus.READY:
            raise GuideError("La guía todavía no está disponible")
        step = next((step for step in guide.steps if step.id == step_id), None)
        if step is None:
            raise GuideError("Paso no encontrado", 404)
        if (step.completed, step.progress_note, step.minutes_spent) == (
            payload.completed,
            payload.note,
            payload.minutes_spent,
        ):
            return await self.read(user_id, project_id, guide_id)
        added_minutes = max(0, payload.minutes_spent - step.minutes_spent)
        step.completed = payload.completed
        step.progress_note = payload.note
        step.minutes_spent = payload.minutes_spent
        self.session.add(
            ProgressEntry(
                project_id=project_id,
                guide_step_id=step_id,
                note=payload.note,
                minutes_spent=added_minutes,
            )
        )
        await self.session.commit()
        return await self.read(user_id, project_id, guide_id)
