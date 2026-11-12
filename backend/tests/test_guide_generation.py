"""Contratos básicos de salida de guías, sin inferencia ni corpus real."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.guide_generation import GeneratedGuide, GeneratedGuideStep


def test_rejects_paints_and_sources_not_supplied_by_backend() -> None:
    paint, source = uuid4(), uuid4()
    guide = GeneratedGuide(
        summary="Guía sintética de pruebas",
        limitations=[],
        steps=[
            GeneratedGuideStep(
                title="Capa base",
                zone="Capa",
                objective="Cubrir la superficie",
                technique="base_coat",
                description="Instrucción sintética",
                continue_when="Cobertura uniforme",
                paint_ids=[paint],
                source_ids=[source],
            )
        ],
    )
    guide.validate_references({paint}, {source})
    with pytest.raises(ValueError, match="pinturas no disponibles"):
        guide.validate_references(set(), {source})
    with pytest.raises(ValueError, match="fuentes no recuperadas"):
        guide.validate_references({paint}, set())


def test_empty_guide_must_explain_limitations() -> None:
    guide = GeneratedGuide(summary="Sin recursos", limitations=[], steps=[])
    with pytest.raises(ValueError, match="limitaciones"):
        guide.validate_references(set(), set())
    guide.limitations = ["Inventario insuficiente"]
    guide.validate_references(set(), set())


@pytest.mark.parametrize(
    "technique",
    ["base_coat", "wash", "layering", "edge_highlight", "drybrush", "glazing", "blending"],
)
def test_painting_step_cannot_bypass_inventory_with_empty_references(technique: str) -> None:
    source = uuid4()
    guide = GeneratedGuide.model_validate(
        {
            "summary": "Prueba",
            "limitations": [],
            "steps": [
                {
                    "title": "Aplicar color",
                    "zone": "tela",
                    "objective": "Pintar",
                    "technique": technique,
                    "description": "Aplicar pintura",
                    "continue_when": "Seco",
                    "paint_ids": [],
                    "source_ids": [str(source)],
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="requieren paint_ids"):
        guide.validate_references(set(), {source})
    guide.steps[0].technique = "other"
    guide.validate_references(set(), {source})


def test_rejects_unexpected_actions() -> None:
    with pytest.raises(ValidationError):
        GeneratedGuide.model_validate(
            {
                "summary": "Prueba",
                "limitations": [],
                "steps": [],
                "execute": "alterar inventario",
            }
        )
