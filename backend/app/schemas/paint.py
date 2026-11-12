"""Esquemas de entrada y salida del catálogo de pinturas."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import FinishType, PaintType

SearchTerm = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class PaintRead(BaseModel):
    """Datos públicos de una pintura del catálogo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand: str
    range_name: str
    name: str
    code: str | None
    hex: str
    paint_type: PaintType
    finish: FinishType
    is_active: bool


class PaintListResponse(BaseModel):
    items: list[PaintRead]
    total: int
    limit: int
    offset: int


class PaintRangeFacet(BaseModel):
    brand: str
    range_name: str


class PaintFacets(BaseModel):
    """Valores disponibles para construir los filtros de la interfaz."""

    brands: list[str]
    ranges: list[PaintRangeFacet]
    paint_types: list[PaintType]
    finishes: list[FinishType]


class SimilarPaintRead(BaseModel):
    paint: PaintRead
    distance: float = Field(ge=0)


class PaintColorSearchResponse(BaseModel):
    """Pinturas ordenadas por proximidad perceptual al color buscado."""

    items: list[SimilarPaintRead]
    total: int
    limit: int
    offset: int
