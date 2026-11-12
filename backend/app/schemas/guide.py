"""Contratos públicos de guías y seguimiento."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GuideStatus


class GuideCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_id: UUID


class GuideProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool
    note: str | None = Field(default=None, max_length=2000)
    minutes_spent: int = Field(default=0, ge=0, le=32767)


class GuideStepRead(BaseModel):
    id: UUID
    position: int
    title: str
    zone: str
    objective: str
    technique: str
    description: str
    continue_when: str
    source_ids: list[str]
    paint_ids: list[UUID]
    time_minutes: int | None
    is_optional: bool
    completed: bool
    progress_note: str | None
    minutes_spent: int


class GuideRead(BaseModel):
    id: UUID
    project_id: UUID
    target_image_id: UUID | None
    status: GuideStatus
    stage: str
    summary: str | None
    limitations: list[str]
    error_message: str | None
    cancel_requested: bool
    context: dict[str, Any]
    sources: list[dict[str, Any]]
    unavailable_paint_ids: list[UUID]
    steps: list[GuideStepRead]
    created_at: datetime


class GuideList(BaseModel):
    items: list[GuideRead]
    corpus_ready: bool
