"""Extracción local y fragmentación del corpus; no ejecuta contenido documental."""

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


class DocumentImportError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentSection:
    location: str
    content: str


def extract_sections(path: Path) -> list[DocumentSection]:
    if path.stat().st_size > 20 * 1024 * 1024:
        raise DocumentImportError("El documento supera 20 MiB")
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        content = path.read_text(encoding="utf-8-sig")
        sections = [
            DocumentSection(f"apartado {i + 1}", value.strip())
            for i, value in enumerate(re.split(r"(?m)(?=^#{1,6} )", content))
            if value.strip()
        ]
    elif suffix == ".docx":
        with ZipFile(path) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > 20 * 1024 * 1024:
                raise DocumentImportError("Contenido DOCX demasiado grande")
            root = ElementTree.fromstring(archive.read(info))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = ["".join(p.itertext()).strip() for p in root.findall(".//w:p", ns)]
        sections = [
            DocumentSection(f"párrafo {i + 1}", value)
            for i, value in enumerate(paragraphs)
            if value
        ]
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            raise DocumentImportError("El PDF está cifrado")
        sections = []
        for index, page in enumerate(reader.pages):
            value = (page.extract_text() or "").strip()
            if not value:
                raise DocumentImportError(f"La página {index + 1} requiere revisión u OCR")
            sections.append(DocumentSection(f"página {index + 1}", value))
    else:
        raise DocumentImportError("Formato admitido: PDF, DOCX, Markdown o TXT")
    if not sections:
        raise DocumentImportError("No se encontró texto para indexar")
    return sections


def chunk_sections(
    sections: list[DocumentSection], size: int = 220, overlap: int = 35
) -> list[DocumentSection]:
    """Fragmenta por palabras; el codificador debe comprobar el límite de tokens."""
    if size <= overlap or overlap < 0:
        raise ValueError("Tamaño de fragmento inválido")
    chunks = []
    for section in sections:
        words = section.content.split()
        for start in range(0, len(words), size - overlap):
            chunks.append(DocumentSection(section.location, " ".join(words[start : start + size])))
            if start + size >= len(words):
                break
    return chunks
