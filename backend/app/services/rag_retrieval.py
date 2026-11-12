"""Recuperación híbrida con corpus real y sintético explícitamente separados."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument


async def retrieve(
    session: AsyncSession,
    query: str,
    vector: list[float],
    model_revision: str,
    *,
    synthetic: bool = False,
) -> list[KnowledgeDocument]:
    conditions = [
        KnowledgeDocument.embedding.is_not(None),
        KnowledgeDocument.doc_metadata["embedding_revision"].astext == model_revision,
        KnowledgeDocument.doc_metadata["synthetic"].astext == str(synthetic).lower(),
        KnowledgeDocument.doc_metadata["active"].astext == "true",
    ]
    semantic = list(
        (
            await session.scalars(
                select(KnowledgeDocument)
                .where(*conditions)
                .order_by(KnowledgeDocument.embedding.cosine_distance(vector))
                .limit(12)
            )
        ).all()
    )
    document = func.to_tsvector("simple", KnowledgeDocument.content)
    terms = func.plainto_tsquery("simple", query)
    lexical = list(
        (
            await session.scalars(
                select(KnowledgeDocument)
                .where(*conditions, document.op("@@")(terms))
                .order_by(func.ts_rank(document, terms).desc())
                .limit(12)
            )
        ).all()
    )
    scores: dict[UUID, float] = {}
    candidates = {item.id: item for item in semantic + lexical}
    for results in (semantic, lexical):
        for rank, item in enumerate(results, 1):
            scores[item.id] = scores.get(item.id, 0) + 1 / (60 + rank)
    return [candidates[key] for key in sorted(scores, key=lambda key: -scores[key])[:6]]
