"""Endpoints de consulta del catálogo de pinturas."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, get_current_user
from app.models.enums import FinishType, PaintType
from app.schemas.paint import (
    PaintColorSearchResponse,
    PaintFacets,
    PaintListResponse,
    PaintRangeFacet,
    PaintRead,
    SimilarPaintRead,
)
from app.services.colors import ColorError
from app.services.paints import PaintFilters, PaintService

router = APIRouter(
    prefix="/paints",
    tags=["paints"],
    dependencies=[Depends(get_current_user)],
)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@router.get("/facets", response_model=PaintFacets)
async def read_facets(session: DbSession) -> PaintFacets:
    """Marcas, gamas y tipos disponibles para los filtros."""
    data = await PaintService(session).facets()
    return PaintFacets(
        brands=data.brands,
        ranges=[
            PaintRangeFacet(brand=brand, range_name=range_name)
            for brand, range_name in data.ranges
        ],
        paint_types=data.paint_types,
        finishes=data.finishes,
    )


@router.get("", response_model=PaintListResponse)
async def list_paints(
    session: DbSession,
    q: Annotated[str | None, Query(max_length=80)] = None,
    brand: Annotated[str | None, Query(max_length=80)] = None,
    range_name: Annotated[str | None, Query(max_length=80)] = None,
    paint_type: PaintType | None = None,
    finish: FinishType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaintListResponse:
    filters = PaintFilters(
        q=_clean(q),
        brand=_clean(brand),
        range_name=_clean(range_name),
        paint_type=paint_type,
        finish=finish,
    )
    items, total = await PaintService(session).search(filters, limit=limit, offset=offset)
    return PaintListResponse(
        items=[PaintRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/by-color", response_model=PaintColorSearchResponse)
async def search_paints_by_color(
    session: DbSession,
    hex_color: Annotated[str, Query(min_length=6, max_length=7)],
    q: Annotated[str | None, Query(max_length=80)] = None,
    brand: Annotated[str | None, Query(max_length=80)] = None,
    range_name: Annotated[str | None, Query(max_length=80)] = None,
    paint_type: PaintType | None = None,
    finish: FinishType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaintColorSearchResponse:
    """Busca tonos exactos y aproximados a un color hexadecimal."""
    filters = PaintFilters(
        q=_clean(q),
        brand=_clean(brand),
        range_name=_clean(range_name),
        paint_type=paint_type,
        finish=finish,
    )
    try:
        items, total = await PaintService(session).search_by_color(
            hex_color,
            filters,
            limit=limit,
            offset=offset,
        )
    except ColorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return PaintColorSearchResponse(
        items=[
            SimilarPaintRead(paint=PaintRead.model_validate(paint), distance=distance)
            for paint, distance in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{paint_id}", response_model=PaintRead)
async def read_paint(paint_id: UUID, session: DbSession) -> PaintRead:
    paint = await PaintService(session).get_active(paint_id)
    if paint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pintura no encontrada",
        )
    return PaintRead.model_validate(paint)


@router.get("/{paint_id}/similar", response_model=list[SimilarPaintRead])
async def list_similar_paints(
    paint_id: UUID,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> list[SimilarPaintRead]:
    service = PaintService(session)
    paint = await service.get_active(paint_id)
    if paint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pintura no encontrada",
        )

    similar = await service.similar(paint, limit=limit)
    return [
        SimilarPaintRead(paint=PaintRead.model_validate(item), distance=distance)
        for item, distance in similar
    ]
