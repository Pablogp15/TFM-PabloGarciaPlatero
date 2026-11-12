"""Lógica de negocio de los proyectos del usuario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.enums import ProjectStatus
from app.models.generation import Generation
from app.models.project import Project, ProjectImage
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.text import escape_like


class ProjectNotFoundError(Exception):
    """El proyecto no existe o pertenece a otro usuario."""


class ProjectDeleteConflictError(Exception):
    """El proyecto no se puede eliminar por una referencia todavía activa."""


@dataclass(frozen=True, slots=True)
class ProjectFilters:
    status: ProjectStatus | None = None
    q: str | None = None


class ProjectService:
    """Casos de uso de proyectos, siempre acotados al usuario autenticado."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_projects(
        self,
        user_id: UUID,
        filters: ProjectFilters,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Project], int]:
        conditions = self._conditions(user_id, filters)

        total = await self._session.scalar(
            select(func.count()).select_from(Project).where(*conditions)
        )

        statement: Select[Project] = (
            select(Project)
            .where(*conditions)
            .order_by(Project.updated_at.desc(), Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return items, int(total or 0)

    async def get_owned(self, user_id: UUID, project_id: UUID) -> Project:
        project = await self._session.scalar(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        if project is None:
            raise ProjectNotFoundError
        return project

    async def create(self, user_id: UUID, payload: ProjectCreate) -> Project:
        project = Project(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            subject=payload.subject,
            scale_mm=payload.scale_mm,
        )
        self._session.add(project)
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def update(
        self,
        user_id: UUID,
        project_id: UUID,
        payload: ProjectUpdate,
    ) -> Project:
        project = await self.get_owned(user_id, project_id)
        changes = payload.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(project, field, value)

        if "status" in changes:
            if project.status is ProjectStatus.COMPLETED:
                project.completed_at = project.completed_at or datetime.now(UTC)
            else:
                project.completed_at = None

        project.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def delete(self, user_id: UUID, project_id: UUID) -> list[str]:
        """Elimina el proyecto y devuelve las claves de sus imágenes.

        Las claves se recogen antes del borrado para poder limpiar el
        almacenamiento después de que la base de datos confirme la operación.
        """
        project = await self.get_owned(user_id, project_id)

        keys = list(
            (
                await self._session.scalars(
                    select(ProjectImage.storage_key).where(
                        ProjectImage.project_id == project.id
                    )
                )
            ).all()
        )

        try:
            # Las generaciones se eliminan primero porque su FK de imagen de
            # origen es RESTRICT: si PostgreSQL borrara las imágenes antes,
            # la cascada del proyecto fallaría. Después, el borrado en SQL
            # deja que las cascadas eliminen imágenes, esquema, guías y
            # entradas de progreso en una sola operación.
            await self._session.execute(
                delete(Generation).where(Generation.project_id == project.id)
            )
            await self._session.execute(delete(Project).where(Project.id == project.id))
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ProjectDeleteConflictError from exc

        return keys

    @staticmethod
    def _conditions(
        user_id: UUID,
        filters: ProjectFilters,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Project.user_id == user_id]

        if filters.status is not None:
            conditions.append(Project.status == filters.status)
        if filters.q:
            pattern = f"%{escape_like(filters.q)}%"
            conditions.append(
                or_(
                    Project.name.ilike(pattern, escape="\\"),
                    Project.subject.ilike(pattern, escape="\\"),
                    Project.description.ilike(pattern, escape="\\"),
                )
            )

        return conditions
