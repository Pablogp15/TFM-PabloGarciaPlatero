"""Esquemas de las imágenes asociadas a un proyecto."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import ImageKind


class ProjectImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    kind: ImageKind
    mime_type: str
    width: int
    height: int
    size_bytes: int
    checksum: str
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        """Ruta autenticada desde la que se sirve la imagen."""
        return f"/api/v1/projects/{self.project_id}/images/{self.id}"


class ProjectImageListResponse(BaseModel):
    items: list[ProjectImageRead]
    total: int
    limit: int
    offset: int
