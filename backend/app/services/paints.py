"""Lógica de negocio del catálogo global de pinturas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.enums import FinishType, PaintType
from app.models.paint import Paint
from app.services.colors import hex_to_lab, normalize_hex
from app.services.text import escape_like


@dataclass(frozen=True, slots=True)
class PaintFilters:
    q: str | None = None
    brand: str | None = None
    range_name: str | None = None
    paint_type: PaintType | None = None
    finish: FinishType | None = None


@dataclass(frozen=True, slots=True)
class PaintFacetsData:
    brands: list[str]
    ranges: list[tuple[str, str]]
    paint_types: list[PaintType]
    finishes: list[FinishType]


class PaintService:
    """Consultas de solo lectura sobre el catálogo compartido."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        filters: PaintFilters,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Paint], int]:
        conditions = self._conditions(filters)

        total = await self._session.scalar(
            select(func.count()).select_from(Paint).where(*conditions)
        )

        statement: Select[Paint] = (
            select(Paint)
            .where(*conditions)
            .order_by(Paint.brand, Paint.range_name, Paint.name)
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return items, int(total or 0)

    async def get_active(self, paint_id: UUID) -> Paint | None:
        return await self._session.scalar(
            select(Paint).where(Paint.id == paint_id, Paint.is_active.is_(True))
        )

    async def facets(self) -> PaintFacetsData:
        active = Paint.is_active.is_(True)

        range_rows = (
            await self._session.execute(
                select(Paint.brand, Paint.range_name)
                .where(active)
                .distinct()
                .order_by(Paint.brand, Paint.range_name)
            )
        ).all()

        brands = list(dict.fromkeys(brand for brand, _ in range_rows))
        ranges = [(brand, range_name) for brand, range_name in range_rows]

        paint_types = list(
            (await self._session.scalars(select(Paint.paint_type).where(active).distinct())).all()
        )
        finishes = list(
            (await self._session.scalars(select(Paint.finish).where(active).distinct())).all()
        )

        return PaintFacetsData(
            brands=brands,
            ranges=ranges,
            paint_types=sorted(paint_types, key=lambda value: value.value),
            finishes=sorted(finishes, key=lambda value: value.value),
        )

    async def similar(
        self,
        paint: Paint,
        *,
        limit: int,
    ) -> list[tuple[Paint, float]]:
        """Pinturas con el color más parecido en espacio CIELAB."""
        target_l, target_a, target_b = self._lab_of(paint)

        distance_sq = (
            (Paint.lab_l - target_l) * (Paint.lab_l - target_l)
            + (Paint.lab_a - target_a) * (Paint.lab_a - target_a)
            + (Paint.lab_b - target_b) * (Paint.lab_b - target_b)
        ).label("distance_sq")

        statement = (
            select(Paint, distance_sq)
            .where(
                Paint.is_active.is_(True),
                Paint.id != paint.id,
                Paint.lab_l.is_not(None),
                Paint.lab_a.is_not(None),
                Paint.lab_b.is_not(None),
            )
            .order_by(distance_sq)
            .limit(limit)
        )

        rows = (await self._session.execute(statement)).all()
        result: list[tuple[Paint, float]] = []
        for paint_row, distance_value in rows:
            if distance_value is None:
                continue
            result.append((paint_row, math.sqrt(float(distance_value))))
        return result

    async def search_by_color(
        self,
        color_hex: str,
        filters: PaintFilters,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Paint, float]], int]:
        """Busca pinturas por distancia perceptual CIELAB al HEX solicitado."""
        target_l, target_a, target_b = hex_to_lab(normalize_hex(color_hex))
        conditions = [
            *self._conditions(filters),
            Paint.lab_l.is_not(None),
            Paint.lab_a.is_not(None),
            Paint.lab_b.is_not(None),
        ]
        distance_sq = (
            (Paint.lab_l - target_l) * (Paint.lab_l - target_l)
            + (Paint.lab_a - target_a) * (Paint.lab_a - target_a)
            + (Paint.lab_b - target_b) * (Paint.lab_b - target_b)
        ).label("distance_sq")

        total = int(
            await self._session.scalar(
                select(func.count()).select_from(Paint).where(*conditions)
            )
            or 0
        )
        statement = (
            select(Paint, distance_sq)
            .where(*conditions)
            .order_by(distance_sq, Paint.brand, Paint.range_name, Paint.name)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            (paint, math.sqrt(float(distance)))
            for paint, distance in rows
            if distance is not None
        ], total

    @staticmethod
    def _conditions(filters: PaintFilters) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Paint.is_active.is_(True)]

        if filters.q:
            pattern = f"%{escape_like(filters.q)}%"
            conditions.append(
                or_(
                    Paint.name.ilike(pattern, escape="\\"),
                    Paint.brand.ilike(pattern, escape="\\"),
                    Paint.range_name.ilike(pattern, escape="\\"),
                    Paint.code.ilike(pattern, escape="\\"),
                )
            )
        if filters.brand:
            conditions.append(Paint.brand == filters.brand)
        if filters.range_name:
            conditions.append(Paint.range_name == filters.range_name)
        if filters.paint_type is not None:
            conditions.append(Paint.paint_type == filters.paint_type)
        if filters.finish is not None:
            conditions.append(Paint.finish == filters.finish)

        return conditions

    @staticmethod
    def _lab_of(paint: Paint) -> tuple[float, float, float]:
        if paint.lab_l is not None and paint.lab_a is not None and paint.lab_b is not None:
            return float(paint.lab_l), float(paint.lab_a), float(paint.lab_b)
        return hex_to_lab(paint.hex)
