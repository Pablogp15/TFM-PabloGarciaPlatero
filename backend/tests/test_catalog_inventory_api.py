"""Pruebas de integración del catálogo y del inventario.

Necesitan PostgreSQL con la extensión ``vector``. Se omiten si no se define
``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.data.paints_catalog import BRANDS, CATALOG
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.services.catalog_seed import seed_catalog

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL no está definida: se omite la prueba con base de datos",
)

EMAIL = "pintor@example.com"
PASSWORD = "contrasena-muy-segura"


def _csrf(client: AsyncClient) -> str:
    token = client.cookies.get("mp_csrf")
    assert token is not None
    return token


async def _register(client: AsyncClient, email: str = EMAIL) -> None:
    csrf = await client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Pintor"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 201


@pytest.fixture
async def transport() -> AsyncIterator[ASGITransport]:
    assert TEST_DATABASE_URL is not None

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_catalog(session)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db

    try:
        yield ASGITransport(app=application)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def test_catalog_queries(transport: ASGITransport) -> None:
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # El catálogo exige sesión, aunque no sea información privada.
        assert (await client.get("/api/v1/paints")).status_code == 401

        await _register(client)

        first_page = await client.get("/api/v1/paints?limit=5")
        assert first_page.status_code == 200
        page = first_page.json()
        assert len(page["items"]) == 5
        assert page["total"] == len(CATALOG)
        assert page["limit"] == 5

        vallejo = await client.get("/api/v1/paints?brand=Vallejo&limit=100")
        assert vallejo.status_code == 200
        assert vallejo.json()["total"] > 0
        assert all(item["brand"] == "Vallejo" for item in vallejo.json()["items"])

        abaddon = await client.get("/api/v1/paints?q=abaddon")
        assert abaddon.status_code == 200
        assert [item["name"] for item in abaddon.json()["items"]] == ["Abaddon Black"]

        metallic = await client.get("/api/v1/paints?paint_type=metallic&limit=100")
        assert metallic.status_code == 200
        assert metallic.json()["total"] > 0
        assert all(item["paint_type"] == "metallic" for item in metallic.json()["items"])

        assert (await client.get("/api/v1/paints?paint_type=inexistente")).status_code == 422

        facets = await client.get("/api/v1/paints/facets")
        assert facets.status_code == 200
        facet_body = facets.json()
        assert set(facet_body["brands"]) == set(BRANDS)
        assert any(
            entry["brand"] == "Citadel" and entry["range_name"] == "Shade"
            for entry in facet_body["ranges"]
        )
        assert "metallic" in facet_body["paint_types"]

        paint_id = abaddon.json()["items"][0]["id"]
        similar = await client.get(f"/api/v1/paints/{paint_id}/similar?limit=3")
        assert similar.status_code == 200
        similar_body = similar.json()
        assert len(similar_body) == 3
        assert all(item["paint"]["id"] != paint_id for item in similar_body)
        distances = [item["distance"] for item in similar_body]
        assert distances == sorted(distances)

        by_color = await client.get("/api/v1/paints/by-color?hex_color=%23FF0000&limit=5")
        assert by_color.status_code == 200
        color_body = by_color.json()
        assert len(color_body["items"]) == 5
        color_distances = [item["distance"] for item in color_body["items"]]
        assert color_distances == sorted(color_distances)
        assert all(item["distance"] >= 0 for item in color_body["items"])

        filtered_color = await client.get(
            "/api/v1/paints/by-color?hex_color=FF0000&brand=Citadel&limit=100"
        )
        assert filtered_color.status_code == 200
        assert all(item["paint"]["brand"] == "Citadel" for item in filtered_color.json()["items"])

        invalid_color = await client.get("/api/v1/paints/by-color?hex_color=not-a-color")
        assert invalid_color.status_code == 422

        assert (await client.get(f"/api/v1/paints/{uuid4()}")).status_code == 404


async def test_inventory_flow_and_ownership(transport: ASGITransport) -> None:
    async with AsyncClient(transport=transport, base_url="http://test") as owner:
        await _register(owner)

        catalog = await owner.get("/api/v1/paints?q=Abaddon&limit=1")
        paint = catalog.json()["items"][0]

        # Sin CSRF no se permite escribir.
        assert (
            await owner.post("/api/v1/inventory", json={"paint_id": paint["id"]})
        ).status_code == 403

        created = await owner.post(
            "/api/v1/inventory",
            json={"paint_id": paint["id"], "quantity": 2},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert created.status_code == 201
        item = created.json()
        assert item["paint"]["id"] == paint["id"]
        assert item["quantity"] == 2
        assert item["running_low"] is False

        # Repetir la petición no duplica la pintura.
        repeated = await owner.post(
            "/api/v1/inventory",
            json={"paint_id": paint["id"], "quantity": 2},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert repeated.status_code == 200
        assert repeated.json()["id"] == item["id"]
        assert repeated.json()["quantity"] == 2

        listing = await owner.get("/api/v1/inventory")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert listing.json()["items"][0]["paint"]["name"] == "Abaddon Black"

        stats = await owner.get("/api/v1/inventory/stats")
        assert stats.status_code == 200
        assert stats.json() == {
            "total_items": 1,
            "total_quantity": 2,
            "owned": 1,
            "running_low": 0,
            "brands": 1,
        }

        updated = await owner.patch(
            f"/api/v1/inventory/{item['id']}",
            json={"quantity": 3, "running_low": True, "notes": "  queda poco  "},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert updated.status_code == 200
        assert updated.json()["quantity"] == 3
        assert updated.json()["running_low"] is True
        assert updated.json()["notes"] == "queda poco"

        assert (
            await owner.patch(
                f"/api/v1/inventory/{item['id']}",
                json={},
                headers={"X-CSRF-Token": _csrf(owner)},
            )
        ).status_code == 422
        assert (
            await owner.patch(
                f"/api/v1/inventory/{item['id']}",
                json={"quantity": None},
                headers={"X-CSRF-Token": _csrf(owner)},
            )
        ).status_code == 422

        filtered = await owner.get("/api/v1/inventory?running_low=true&brand=Citadel&q=abaddon")
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1

        stats = await owner.get("/api/v1/inventory/stats")
        assert stats.json()["running_low"] == 1
        assert stats.json()["total_quantity"] == 3

        # Otro usuario no puede leer ni modificar el elemento ajeno.
        async with AsyncClient(transport=transport, base_url="http://test") as other:
            await _register(other, "otro@example.com")

            assert (await other.get("/api/v1/inventory")).json()["total"] == 0
            assert (
                await other.patch(
                    f"/api/v1/inventory/{item['id']}",
                    json={"quantity": 5},
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404
            assert (
                await other.delete(
                    f"/api/v1/inventory/{item['id']}",
                    headers={"X-CSRF-Token": _csrf(other)},
                )
            ).status_code == 404

        unknown_paint = await owner.post(
            "/api/v1/inventory",
            json={"paint_id": str(uuid4())},
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert unknown_paint.status_code == 404

        deleted = await owner.delete(
            f"/api/v1/inventory/{item['id']}",
            headers={"X-CSRF-Token": _csrf(owner)},
        )
        assert deleted.status_code == 204
        assert (await owner.get("/api/v1/inventory")).json()["total"] == 0

        empty_stats = await owner.get("/api/v1/inventory/stats")
        assert empty_stats.json() == {
            "total_items": 0,
            "total_quantity": 0,
            "owned": 0,
            "running_low": 0,
            "brands": 0,
        }


async def test_wishlist_is_independent_and_private(transport: ASGITransport) -> None:
    async with AsyncClient(transport=transport, base_url="http://test") as owner:
        assert (await owner.get("/api/v1/wishlist")).status_code == 401
        await _register(owner)
        paints = (await owner.get("/api/v1/paints?limit=2")).json()["items"]
        paint_id = paints[0]["id"]
        headers = {"X-CSRF-Token": _csrf(owner)}
        assert (
            await owner.post("/api/v1/wishlist", json={"paint_id": paint_id})
        ).status_code == 403
        for _ in range(2):
            assert (
                await owner.post("/api/v1/wishlist", json={"paint_id": paint_id}, headers=headers)
            ).status_code == 204
        assert (await owner.get("/api/v1/wishlist")).json()["total"] == 1
        assert (await owner.get("/api/v1/wishlist/paint-ids")).json() == [paint_id]
        assert (await owner.get("/api/v1/inventory")).json()["total"] == 0
        assert (await owner.get("/api/v1/inventory/stats")).json()["total_quantity"] == 0

        owned = (
            await owner.post("/api/v1/inventory", json={"paint_id": paint_id}, headers=headers)
        ).json()
        await owner.post("/api/v1/inventory", json={"paint_id": paints[1]["id"]}, headers=headers)
        assert (await owner.get("/api/v1/inventory?running_low=true")).json()["total"] == 0
        marked = await owner.patch(
            f"/api/v1/inventory/{owned['id']}", json={"running_low": True}, headers=headers
        )
        assert marked.status_code == 200
        assert marked.json()["quantity"] == 1
        assert (await owner.get("/api/v1/inventory?running_low=true")).json()["total"] == 1
        assert (await owner.get("/api/v1/inventory?running_low=false")).json()["total"] == 1
        assert (await owner.get("/api/v1/inventory/stats")).json()["owned"] == 2
        assert (await owner.get("/api/v1/wishlist")).json()["total"] == 1
        assert (
            await owner.patch(
                f"/api/v1/inventory/{owned['id']}", json={"running_low": None}, headers=headers
            )
        ).status_code == 422

        async with AsyncClient(transport=transport, base_url="http://test") as other:
            await _register(other, "otro@example.com")
            assert (await other.get("/api/v1/wishlist")).json()["total"] == 0
            assert (await other.get("/api/v1/wishlist/paint-ids")).json() == []
            assert (
                await other.delete(
                    f"/api/v1/wishlist/{paint_id}", headers={"X-CSRF-Token": _csrf(other)}
                )
            ).status_code == 204
        assert (await owner.get("/api/v1/wishlist")).json()["total"] == 1
        assert (
            await owner.post("/api/v1/wishlist", json={"paint_id": str(uuid4())}, headers=headers)
        ).status_code == 404
        assert (await owner.get("/api/v1/wishlist?limit=0")).status_code == 422
        assert (await owner.get("/api/v1/wishlist?offset=1")).json()["items"] == []
        assert (await owner.delete(f"/api/v1/wishlist/{paint_id}")).status_code == 403
        await owner.delete(f"/api/v1/wishlist/{paint_id}", headers=headers)
        assert (await owner.get("/api/v1/inventory")).json()["total"] == 2
        await owner.post("/api/v1/wishlist", json={"paint_id": paint_id}, headers=headers)
        await owner.delete(f"/api/v1/inventory/{owned['id']}", headers=headers)
        assert (await owner.get("/api/v1/wishlist")).json()["total"] == 1
