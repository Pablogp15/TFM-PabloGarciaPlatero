"""Lógica de negocio del inventario personal de pinturas."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, distinct, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models.paint import Paint, UserPaint
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate
from app.services.text import escape_like


class PaintNotFoundError(Exception):
    """La pintura indicada no existe o está desactivada."""


class InventoryItemNotFoundError(Exception):
    """El elemento no existe o pertenece a otro usuario."""


@dataclass(frozen=True, slots=True)
class InventoryFilters:
    running_low: bool | None = None
    brand: str | None = None
    q: str | None = None


@dataclass(frozen=True, slots=True)
class InventoryStatsData:
    total_items: int
    total_quantity: int
    owned: int
    running_low: int
    brands: int


class InventoryService:
    """Casos de uso del inventario, siempre acotados al usuario autenticado."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_items(
        self,
        user_id: UUID,
        filters: InventoryFilters,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[UserPaint], int]:
        conditions = self._conditions(user_id, filters)

        total = await self._session.scalar(
            select(func.count())
            .select_from(UserPaint)
            .join(Paint, UserPaint.paint_id == Paint.id)
            .where(*conditions)
        )

        statement: Select[UserPaint] = (
            select(UserPaint)
            .join(Paint, UserPaint.paint_id == Paint.id)
            .where(*conditions)
            .options(selectinload(UserPaint.paint))
            .order_by(Paint.brand, Paint.range_name, Paint.name)
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return items, int(total or 0)

    async def add(
        self,
        user_id: UUID,
        payload: InventoryItemCreate,
    ) -> tuple[UserPaint, bool]:
        """Añade una pintura o devuelve la existente sin duplicarla."""
        paint = await self._session.get(Paint, payload.paint_id)
        if paint is None or not paint.is_active:
            raise PaintNotFoundError

        existing = await self._find_item(user_id, payload.paint_id)
        if existing is not None:
            return existing, False

        item = UserPaint(
            user_id=user_id,
            paint=paint,
            quantity=payload.quantity,
            running_low=payload.running_low,
            notes=payload.notes,
        )
        self._session.add(item)

        try:
            await self._session.flush()
        except IntegrityError:
            # Dos peticiones simultáneas pueden pasar la comprobación previa:
            # la restricción única decide y se devuelve la fila ganadora.
            await self._session.rollback()
            existing = await self._find_item(user_id, payload.paint_id)
            if existing is not None:
                return existing, False
            raise

        await self._session.commit()
        return item, True

    async def update(
        self,
        user_id: UUID,
        item_id: UUID,
        payload: InventoryItemUpdate,
    ) -> UserPaint:
        item = await self._get_owned(user_id, item_id)

        if "quantity" in payload.model_fields_set:
            assert payload.quantity is not None
            item.quantity = payload.quantity
        if "running_low" in payload.model_fields_set:
            assert payload.running_low is not None
            item.running_low = payload.running_low
        if "notes" in payload.model_fields_set:
            item.notes = payload.notes

        await self._session.commit()
        await self._session.refresh(item, attribute_names=["updated_at"])
        return item

    async def delete(self, user_id: UUID, item_id: UUID) -> None:
        item = await self._get_owned(user_id, item_id)
        await self._session.delete(item)
        await self._session.commit()

    async def stats(self, user_id: UUID) -> InventoryStatsData:
        rows = (
            await self._session.execute(
                select(
                    UserPaint.running_low,
                    func.count(),
                    func.coalesce(func.sum(UserPaint.quantity), 0),
                )
                .where(UserPaint.user_id == user_id)
                .group_by(UserPaint.running_low)
            )
        ).all()

        counts = {False: 0, True: 0}
        total_quantity = 0
        for status, count, quantity in rows:
            counts[status] = int(count)
            total_quantity += int(quantity)

        brands = await self._session.scalar(
            select(func.count(distinct(Paint.brand)))
            .select_from(UserPaint)
            .join(Paint, UserPaint.paint_id == Paint.id)
            .where(UserPaint.user_id == user_id)
        )

        return InventoryStatsData(
            total_items=sum(counts.values()),
            total_quantity=total_quantity,
            owned=sum(counts.values()),
            running_low=counts[True],
            brands=int(brands or 0),
        )

    async def _find_item(self, user_id: UUID, paint_id: UUID) -> UserPaint | None:
        return await self._session.scalar(
            select(UserPaint)
            .where(UserPaint.user_id == user_id, UserPaint.paint_id == paint_id)
            .options(selectinload(UserPaint.paint))
        )

    async def _get_owned(self, user_id: UUID, item_id: UUID) -> UserPaint:
        item = await self._session.scalar(
            select(UserPaint)
            .where(UserPaint.id == item_id, UserPaint.user_id == user_id)
            .options(selectinload(UserPaint.paint))
        )
        if item is None:
            raise InventoryItemNotFoundError
        return item

    @staticmethod
    def _conditions(
        user_id: UUID,
        filters: InventoryFilters,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [UserPaint.user_id == user_id]

        if filters.running_low is not None:
            conditions.append(UserPaint.running_low == filters.running_low)
        if filters.brand:
            conditions.append(Paint.brand == filters.brand)
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

        return conditions
