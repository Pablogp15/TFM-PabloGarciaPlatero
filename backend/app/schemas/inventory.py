"""Esquemas de entrada y salida del inventario personal."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.paint import PaintRead


class InventoryItemCreate(BaseModel):
    paint_id: UUID
    quantity: int = Field(default=1, ge=0, le=999)
    running_low: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class InventoryItemUpdate(BaseModel):
    """Actualización parcial. Solo se aplican los campos enviados."""

    quantity: int | None = Field(default=None, ge=0, le=999)
    running_low: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def _quantity_not_null(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("La cantidad no puede ser nula")
        return value

    @field_validator("running_low")
    @classmethod
    def _running_low_not_null(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("El indicador no puede ser nulo")
        return value

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> InventoryItemUpdate:
        if not self.model_fields_set:
            raise ValueError("Indica al menos un campo para actualizar")
        return self


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    paint: PaintRead
    quantity: int
    running_low: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class InventoryListResponse(BaseModel):
    items: list[InventoryItemRead]
    total: int
    limit: int
    offset: int


class InventoryStats(BaseModel):
    total_items: int
    total_quantity: int
    owned: int
    running_low: int
    brands: int
