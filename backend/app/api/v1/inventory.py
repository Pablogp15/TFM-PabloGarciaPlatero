"""Endpoints del inventario personal de pinturas."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    InventoryListResponse,
    InventoryStats,
)
from app.services.inventory import (
    InventoryFilters,
    InventoryItemNotFoundError,
    InventoryService,
    PaintNotFoundError,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@router.get("/stats", response_model=InventoryStats)
async def read_inventory_stats(current_user: CurrentUser, session: DbSession) -> InventoryStats:
    data = await InventoryService(session).stats(current_user.id)
    return InventoryStats(
        total_items=data.total_items,
        total_quantity=data.total_quantity,
        owned=data.owned,
        running_low=data.running_low,
        brands=data.brands,
    )


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    current_user: CurrentUser,
    session: DbSession,
    running_low: bool | None = None,
    brand: Annotated[str | None, Query(max_length=80)] = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryListResponse:
    filters = InventoryFilters(running_low=running_low, brand=_clean(brand), q=_clean(q))
    items, total = await InventoryService(session).list_items(
        current_user.id,
        filters,
        limit=limit,
        offset=offset,
    )
    return InventoryListResponse(
        items=[InventoryItemRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=InventoryItemRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def add_inventory_item(
    payload: InventoryItemCreate,
    response: Response,
    current_user: CurrentUser,
    session: DbSession,
) -> InventoryItemRead:
    """Añade una pintura. Si ya estaba, devuelve la existente sin duplicarla."""
    try:
        item, created = await InventoryService(session).add(current_user.id, payload)
    except PaintNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Pintura no encontrada",
        ) from exc

    if not created:
        response.status_code = http_status.HTTP_200_OK
    return InventoryItemRead.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=InventoryItemRead,
    dependencies=[Depends(require_csrf)],
)
async def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> InventoryItemRead:
    try:
        item = await InventoryService(session).update(current_user.id, item_id, payload)
    except InventoryItemNotFoundError as exc:
        # Un 404 también evita revelar si el recurso existe y es de otro usuario.
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Pintura no encontrada en el inventario",
        ) from exc
    return InventoryItemRead.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_inventory_item(
    item_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    try:
        await InventoryService(session).delete(current_user.id, item_id)
    except InventoryItemNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Pintura no encontrada en el inventario",
        ) from exc
