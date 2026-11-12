"""Contratos de la lista personal de deseos."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.paint import PaintRead


class WishlistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    paint: PaintRead
    created_at: datetime


class WishlistList(BaseModel):
    items: list[WishlistItemRead]
    total: int
    limit: int
    offset: int


class WishlistCreate(BaseModel):
    paint_id: UUID
