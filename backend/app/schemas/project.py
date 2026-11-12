"""Esquemas de entrada y salida de proyectos y de su esquema de color."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import ProjectStatus, SchemeRole
from app.schemas.paint import PaintRead
from app.services.colors import normalize_hex

ProjectName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
ProjectSubject = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class ProjectCreate(BaseModel):
    name: ProjectName
    description: str | None = Field(default=None, max_length=4000)
    subject: ProjectSubject | None = None
    scale_mm: int | None = Field(default=None, ge=1, le=2000)

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @field_validator("subject")
    @classmethod
    def _normalize_subject(cls, value: str | None) -> str | None:
        return _clean_optional(value)


class ProjectUpdate(BaseModel):
    """Actualización parcial. Solo se aplican los campos enviados."""

    name: ProjectName | None = None
    description: str | None = Field(default=None, max_length=4000)
    subject: ProjectSubject | None = None
    scale_mm: int | None = Field(default=None, ge=1, le=2000)
    status: ProjectStatus | None = None

    @field_validator("name")
    @classmethod
    def _name_not_null(cls, value: ProjectName | None) -> ProjectName:
        if value is None:
            raise ValueError("El nombre no puede ser nulo")
        return value

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, value: ProjectStatus | None) -> ProjectStatus:
        if value is None:
            raise ValueError("El estado no puede ser nulo")
        if value is ProjectStatus.GENERATING:
            # Reservado al trabajador de generación de la fase 4.
            raise ValueError("El estado 'generating' solo lo asigna el sistema")
        return value

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @field_validator("subject")
    @classmethod
    def _normalize_subject(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> ProjectUpdate:
        if not self.model_fields_set:
            raise ValueError("Indica al menos un campo para actualizar")
        return self


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    subject: str | None
    scale_mm: int | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ProjectListResponse(BaseModel):
    items: list[ProjectRead]
    total: int
    limit: int
    offset: int


class SchemeColorInput(BaseModel):
    """Color elegido para un rol del esquema.

    Debe indicar una pintura del catálogo, un color hexadecimal o ambos. El
    hexadecimal tiene prioridad cuando se envían los dos.
    """

    role: SchemeRole = SchemeRole.OTHER
    paint_id: UUID | None = None
    hex_override: str | None = None
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("hex_override")
    @classmethod
    def _normalize_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_hex(value)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @model_validator(mode="after")
    def _require_color(self) -> SchemeColorInput:
        if self.paint_id is None and self.hex_override is None:
            raise ValueError("Cada color debe indicar una pintura o un valor hexadecimal")
        return self


class SchemeColorsReplace(BaseModel):
    """Sustituye por completo el esquema de color del proyecto."""

    colors: list[SchemeColorInput] = Field(default_factory=list, max_length=32)


class SchemeColorRead(BaseModel):
    id: UUID
    position: int
    role: SchemeRole
    paint: PaintRead | None
    hex_override: str | None
    effective_hex: str
    notes: str | None
