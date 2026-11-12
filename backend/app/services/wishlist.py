"""Deseados acotados al usuario y sin efectos sobre el inventario."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paint import Paint, WishlistItem
from app.services.inventory import PaintNotFoundError


class WishlistService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def paint_ids(self, user_id: UUID) -> list[UUID]:
        return list(
            (
                await self._session.scalars(
                    select(WishlistItem.paint_id).where(WishlistItem.user_id == user_id)
                )
            ).all()
        )

    async def list_items(
        self, user_id: UUID, limit: int, offset: int
    ) -> tuple[list[WishlistItem], int]:
        condition = WishlistItem.user_id == user_id
        total = await self._session.scalar(
            select(func.count()).select_from(WishlistItem).where(condition)
        )
        items = await self._session.scalars(
            select(WishlistItem)
            .where(condition)
            .options(selectinload(WishlistItem.paint))
            .order_by(WishlistItem.created_at.desc(), WishlistItem.paint_id)
            .limit(limit)
            .offset(offset)
        )
        return list(items.all()), int(total or 0)

    async def add(self, user_id: UUID, paint_id: UUID) -> None:
        paint = await self._session.get(Paint, paint_id)
        if paint is None or not paint.is_active:
            raise PaintNotFoundError
        await self._session.execute(
            insert(WishlistItem).values(user_id=user_id, paint_id=paint_id).on_conflict_do_nothing()
        )
        await self._session.commit()

    async def remove(self, user_id: UUID, paint_id: UUID) -> None:
        item = await self._session.get(WishlistItem, (user_id, paint_id))
        if item is not None:
            await self._session.delete(item)
            await self._session.commit()
