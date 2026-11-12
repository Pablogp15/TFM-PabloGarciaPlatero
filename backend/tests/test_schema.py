"""Pruebas del esquema que no requieren una base de datos activa."""

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

import app.models  # noqa: F401
from app.db.base import Base

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "paints",
    "user_paints",
    "wishlist_items",
    "projects",
    "project_scheme_colors",
    "project_images",
    "generations",
    "generation_events",
    "guides",
    "guide_steps",
    "guide_step_paints",
    "progress_entries",
    "knowledge_documents",
}


def test_all_expected_tables_are_declared() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_constraint_has_an_explicit_name() -> None:
    unnamed: list[str] = []

    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if constraint.name is None:
                unnamed.append(f"{table.name}.{type(constraint).__name__}")

    assert unnamed == []


def test_naming_convention_is_applied() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                assert constraint.name.startswith(f"uq_{table.name}_")
            elif isinstance(constraint, CheckConstraint):
                assert constraint.name.startswith(f"ck_{table.name}_")


def test_indexes_are_named() -> None:
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            assert isinstance(index, Index)
            assert index.name is not None


def test_knowledge_documents_has_hnsw_index() -> None:
    table = Base.metadata.tables["knowledge_documents"]
    hnsw = [
        index
        for index in table.indexes
        if index.dialect_options["postgresql"]["using"] == "hnsw"
    ]

    assert len(hnsw) == 1
    assert hnsw[0].dialect_options["postgresql"]["ops"] == {"embedding": "vector_cosine_ops"}
