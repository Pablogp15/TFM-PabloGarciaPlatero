"""Esquemas de entrada y salida de las generaciones de imagen."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)

from app.models.enums import GenerationStage, GenerationStatus, QualityMode

GenerationPrompt = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
NegativePrompt = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class GenerationCreate(BaseModel):
    """Petición de generación. Los límites coinciden con los del servicio GPU."""

    source_image_id: UUID
    prompt: GenerationPrompt
    negative_prompt: NegativePrompt | None = None
    quality: QualityMode = QualityMode.DRAFT
    num_inference_steps: int | None = Field(default=None, ge=8, le=40)
    width: int | None = Field(default=None, ge=512, le=1024, multiple_of=64)
    height: int | None = Field(default=None, ge=512, le=1024, multiple_of=64)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("negative_prompt")
    @classmethod
    def _clean_negative_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_image_id: UUID
    result_image_id: UUID | None
    provider: str
    model_name: str
    quality: QualityMode
    prompt: str
    negative_prompt: str | None
    params: dict[str, Any]
    status: GenerationStatus
    progress_stage: GenerationStage
    progress_percent: int
    job_id: str | None
    estimated_seconds: int | None
    model_load_ms: int | None
    inference_ms: int | None
    vram_peak_mb: int | None
    error_code: str | None
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def result_url(self) -> str | None:
        """Ruta autenticada de la imagen generada, si ya existe."""
        if self.result_image_id is None:
            return None
        return f"/api/v1/projects/{self.project_id}/images/{self.result_image_id}"


class GenerationListResponse(BaseModel):
    items: list[GenerationRead]
    total: int
    limit: int
    offset: int
