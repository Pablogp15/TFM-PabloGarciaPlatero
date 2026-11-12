"""Salida estructurada y validación de las referencias de una guía RAG."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TechniqueType


class VisualZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    material: str = Field(min_length=1, max_length=120)
    color: str = Field(min_length=1, max_length=120)
    uncertainty: str | None = Field(default=None, max_length=500)


class VisualAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[VisualZone] = Field(max_length=30)
    limitations: list[str] = Field(max_length=20)


class GeneratedGuideStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    zone: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=500)
    technique: TechniqueType = Field(
        description=(
            "Técnica del paso; other para revisión de montaje, limpieza "
            "o sujeción sin pintura"
        )
    )
    description: str = Field(min_length=1, max_length=4000)
    continue_when: str = Field(min_length=1, max_length=500)
    paint_ids: list[UUID] = Field(
        max_length=20,
        description=(
            "Identificadores exactos de inventory utilizados al aplicar pintura. "
            "Vacío solo en pasos sin pintura."
        ),
    )
    source_ids: list[UUID] = Field(min_length=1, max_length=6)
    time_minutes: int | None = Field(default=None, ge=0, le=1440)
    is_optional: bool = False

    @field_validator("title", "zone", "objective", "description", "continue_when")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El texto no puede estar vacío")
        return value


class GeneratedGuide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    limitations: list[str] = Field(max_length=20)
    steps: list[GeneratedGuideStep] = Field(max_length=30)

    def validate_references(
        self, available_paints: set[UUID], retrieved_sources: set[UUID]
    ) -> None:
        """Solo acepta referencias suministradas por el backend al modelo.

        Esta comprobación no demuestra que la fuente respalde semánticamente
        la instrucción ni sustituye una revisión experta del contenido.
        """
        if not self.steps and not self.limitations:
            raise ValueError("Una guía sin pasos debe explicar sus limitaciones")
        for step in self.steps:
            if (
                step.technique
                in {
                    TechniqueType.BASE_COAT,
                    TechniqueType.WASH,
                    TechniqueType.LAYERING,
                    TechniqueType.EDGE_HIGHLIGHT,
                    TechniqueType.DRYBRUSH,
                    TechniqueType.GLAZING,
                    TechniqueType.BLENDING,
                }
                and not step.paint_ids
            ):
                raise ValueError(
                    "Los pasos de pintado requieren paint_ids; "
                    "la preparación sin pintura utiliza other"
                )
            if not set(step.paint_ids) <= available_paints:
                raise ValueError("La guía utiliza pinturas no disponibles")
            if not set(step.source_ids) <= retrieved_sources:
                raise ValueError("La guía cita fuentes no recuperadas")
            if len(set(step.paint_ids)) != len(step.paint_ids):
                raise ValueError("La guía contiene pinturas duplicadas en un paso")
