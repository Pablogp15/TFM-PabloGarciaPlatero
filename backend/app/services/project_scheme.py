"""Lógica de negocio del esquema de color de un proyecto."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paint import Paint
from app.models.project import ProjectSchemeColor
from app.schemas.project import SchemeColorInput
from app.services.projects import ProjectService


class SchemePaintNotFoundError(Exception):
    """Alguna de las pinturas indicadas no existe o está desactivada."""


class ProjectSchemeService:
    """Sustituye el esquema completo para que siempre sea coherente."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_colors(
        self, user_id: UUID, project_id: UUID
    ) -> list[ProjectSchemeColor]:
        await ProjectService(self._session).get_owned(user_id, project_id)

        statement = (
            select(ProjectSchemeColor)
            .where(ProjectSchemeColor.project_id == project_id)
            .options(selectinload(ProjectSchemeColor.paint))
            .order_by(ProjectSchemeColor.position)
        )
        return list((await self._session.scalars(statement)).all())

    async def replace(
        self,
        user_id: UUID,
        project_id: UUID,
        colors: list[SchemeColorInput],
    ) -> list[ProjectSchemeColor]:
        project = await ProjectService(self._session).get_owned(user_id, project_id)

        paint_ids = {color.paint_id for color in colors if color.paint_id is not None}
        paints: dict[UUID, Paint] = {}
        if paint_ids:
            rows = (
                await self._session.scalars(
                    select(Paint).where(
                        Paint.id.in_(paint_ids),
                        Paint.is_active.is_(True),
                    )
                )
            ).all()
            paints = {paint.id: paint for paint in rows}
            if len(paints) != len(paint_ids):
                raise SchemePaintNotFoundError

        await self._session.execute(
            delete(ProjectSchemeColor).where(
                ProjectSchemeColor.project_id == project.id
            )
        )

        new_colors: list[ProjectSchemeColor] = []
        for position, color in enumerate(colors):
            row = ProjectSchemeColor(
                project_id=project.id,
                position=position,
                role=color.role,
                paint=paints[color.paint_id] if color.paint_id is not None else None,
                hex_override=color.hex_override,
                notes=color.notes,
            )
            self._session.add(row)
            new_colors.append(row)

        project.updated_at = datetime.now(UTC)
        await self._session.commit()
        return new_colors
