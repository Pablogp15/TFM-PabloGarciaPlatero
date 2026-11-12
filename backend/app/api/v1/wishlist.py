"""API privada de deseados; las escrituras requieren CSRF."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas.wishlist import WishlistCreate, WishlistItemRead, WishlistList
from app.services.inventory import PaintNotFoundError
from app.services.wishlist import WishlistService

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("/paint-ids", response_model=list[UUID])
async def read_paint_ids(current_user: CurrentUser, session: DbSession) -> list[UUID]:
    return await WishlistService(session).paint_ids(current_user.id)


@router.get("", response_model=WishlistList)
async def list_wishlist(
    current_user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WishlistList:
    items, total = await WishlistService(session).list_items(current_user.id, limit, offset)
    return WishlistList(
        items=[WishlistItemRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=204, dependencies=[Depends(require_csrf)])
async def add_wishlist(
    payload: WishlistCreate, current_user: CurrentUser, session: DbSession
) -> None:
    try:
        await WishlistService(session).add(current_user.id, payload.paint_id)
    except PaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pintura no encontrada") from exc


@router.delete("/{paint_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def remove_wishlist(paint_id: UUID, current_user: CurrentUser, session: DbSession) -> None:
    await WishlistService(session).remove(current_user.id, paint_id)
