"""Importa documentos locales con manifiesto y versiones reproducibles."""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.enums import KnowledgeCategory
from app.models.knowledge import KnowledgeDocument
from app.services.rag_documents import extract_sections
from app.services.rag_embeddings import LocalEmbeddings


async def import_document(manifest_path: Path, model_path: str, revision: str) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    for key in ("file", "document_key", "title", "author", "source", "permission", "language"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"Falta el campo {key} del manifiesto")
    if len(manifest["document_key"]) > 80 or len(manifest["title"]) > 200:
        raise ValueError("Identificador o título demasiado largo")
    path = (manifest_path.parent / manifest["file"]).resolve()
    sections = extract_sections(path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    key = (
        manifest["document_key"] + ":" + hashlib.sha256((checksum + revision).encode()).hexdigest()
    )
    encoder = LocalEmbeddings(model_path)
    chunks = [
        (section.location, part) for section in sections for part in encoder.split(section.content)
    ]
    if not chunks or len(chunks) > 10000:
        raise ValueError("Número de fragmentos fuera de los límites")
    vectors = encoder.encode([content for _, content in chunks])
    synthetic = manifest.get("synthetic", False)
    if not isinstance(synthetic, bool):
        raise ValueError("synthetic debe ser booleano")
    async with get_session_factory()() as session:
        existing = list(
            (
                await session.scalars(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.doc_metadata["logical_key"].astext
                        == manifest["document_key"],
                        KnowledgeDocument.doc_metadata["synthetic"].astext
                        == str(synthetic).lower(),
                    )
                )
            ).all()
        )
        for item in existing:
            item.doc_metadata = {**item.doc_metadata, "active": item.document_key == key}
        if any(item.document_key == key for item in existing):
            await session.commit()
            return 0
        for index, ((location, content), vector) in enumerate(zip(chunks, vectors, strict=True)):
            session.add(
                KnowledgeDocument(
                    document_key=key,
                    chunk_index=index,
                    title=manifest["title"],
                    category=KnowledgeCategory.TECHNIQUE,
                    content=content,
                    embedding=vector,
                    doc_metadata={
                        name: manifest[name]
                        for name in ("author", "source", "permission", "language")
                    }
                    | {
                        "logical_key": manifest["document_key"],
                        "checksum": checksum,
                        "location": location,
                        "embedding_revision": revision,
                        "synthetic": synthetic,
                        "active": True,
                    },
                )
            )
        await session.commit()
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    count = asyncio.run(import_document(args.manifest, args.model_path, args.revision))
    print(f"Fragmentos importados: {count}")


if __name__ == "__main__":
    main()
