"""Verifica que la separación conserva las pinturas y los deseados existentes."""

import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

import app.models  # noqa: F401
from app.db.base import Base


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Requiere base de pruebas")
def test_migrate_legacy_inventory() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(url)
    spec = importlib.util.spec_from_file_location(
        "wishlist_migration",
        Path(__file__).parents[1] / "alembic/versions/0004_wishlist.py",
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.drop_all(connection)
            Base.metadata.create_all(connection)
            context = MigrationContext.configure(
                connection, opts={"target_metadata": Base.metadata}
            )
            with Operations.context(context):
                migration.downgrade()
                user_id = uuid4()
                connection.execute(
                    text(
                        "INSERT INTO users (id, email, password_hash, display_name) "
                        "VALUES (:id, 'migration@example.com', 'test-hash', 'Prueba')"
                    ),
                    {"id": user_id},
                )
                ids = []
                for index, status in enumerate(("owned", "running_low", "wishlist")):
                    paint_id = uuid4()
                    ids.append(paint_id)
                    connection.execute(
                        text(
                            "INSERT INTO paints (id, brand, name, hex) "
                            "VALUES (:id, 'Prueba', :name, '#123456')"
                        ),
                        {"id": paint_id, "name": str(index)},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO user_paints (user_id, paint_id, status, quantity, notes) "
                            "VALUES (:user_id, :paint_id, :status, 2, 'conservar')"
                        ),
                        {"user_id": user_id, "paint_id": paint_id, "status": status},
                    )
                migration.upgrade()
            rows = connection.execute(
                text("SELECT paint_id, running_low, quantity, notes FROM user_paints")
            ).all()
            assert {(row.paint_id, row.running_low) for row in rows} == {
                (ids[0], False),
                (ids[1], True),
            }
            assert all(row.quantity == 2 and row.notes == "conservar" for row in rows)
            assert (
                connection.execute(text("SELECT paint_id FROM wishlist_items")).scalar_one()
                == ids[2]
            )
            Base.metadata.drop_all(connection)
    finally:
        engine.dispose()
