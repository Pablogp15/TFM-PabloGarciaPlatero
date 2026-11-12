"""Pruebas de extracción local y contrato con el modelo de guías."""

import json
from pathlib import Path

import httpx
import pytest

from app.schemas.guide_generation import VisualAnalysis
from app.services.rag_documents import DocumentImportError, chunk_sections, extract_sections
from app.services.rag_model import OllamaGuideModel, RagModelError


def test_text_sections_preserve_location_and_overlap(tmp_path: Path) -> None:
    document = tmp_path / "tecnicas.md"
    document.write_text(
        "# Base\nuno dos tres cuatro cinco seis\n# Luces\nsiete ocho", encoding="utf-8"
    )
    sections = extract_sections(document)
    chunks = chunk_sections(sections, size=5, overlap=2)
    assert len(sections) == 2
    assert chunks[0].location == chunks[1].location
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]
    assert chunks[-1].location != chunks[0].location


def test_empty_document_is_rejected(tmp_path: Path) -> None:
    document = tmp_path / "empty.txt"
    document.write_text("   ", encoding="utf-8")
    with pytest.raises(DocumentImportError):
        extract_sections(document)


async def test_ollama_requests_cpu_and_structured_vision() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        assert data["options"]["num_gpu"] == 0
        assert data["format"]["type"] == "object"
        assert data["messages"][1]["images"] == ["aW1hZ2U="]
        assert "tools" not in data
        return httpx.Response(
            200, json={"message": {"content": '{"zones":[],"limitations":["Prueba"]}'}}
        )

    model = OllamaGuideModel("http://ollama:11434", "test", transport=httpx.MockTransport(handle))
    result = await model.generate(VisualAnalysis, "Analiza", {}, b"image")
    assert result.limitations == ["Prueba"]


async def test_invalid_model_response_is_controlled() -> None:
    model = OllamaGuideModel(
        "http://ollama:11434",
        "test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"message": {"content": "invalid"}})
        ),
    )
    with pytest.raises(RagModelError):
        await model.generate(VisualAnalysis, "Analiza", {})
