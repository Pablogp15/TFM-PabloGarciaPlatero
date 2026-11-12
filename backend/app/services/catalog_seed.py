"""Sincronización idempotente del catálogo inicial de pinturas."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.paints_catalog import CATALOG
from app.models.paint import Paint
from app.services.colors import hex_to_lab


@dataclass(frozen=True, slots=True)
class SeedResult:
    total: int
    created: int
    updated: int


async def seed_catalog(session: AsyncSession) -> SeedResult:
    """Inserta o actualiza el catálogo sin duplicar pinturas.

    La clave natural es ``(brand, range_name, name)``. Si una pintura ya existe
    se actualizan sus datos de color y clasificación, pero se conserva su
    identificador para no romper los inventarios que la referencian.
    """
    existing = {
        (brand, range_name, name)
        for brand, range_name, name in (
            await session.execute(select(Paint.brand, Paint.range_name, Paint.name))
        ).all()
    }

    rows = []
    for seed in CATALOG:
        lab_l, lab_a, lab_b = hex_to_lab(seed.hex)
        rows.append(
            {
                "brand": seed.brand,
                "range_name": seed.range_name,
                "name": seed.name,
                "code": seed.code,
                "hex": seed.hex.upper(),
                "paint_type": seed.paint_type,
                "finish": seed.finish,
                "lab_l": lab_l,
                "lab_a": lab_a,
                "lab_b": lab_b,
                "is_active": True,
            }
        )

    statement = insert(Paint).values(rows)
    excluded = statement.excluded
    statement = statement.on_conflict_do_update(
        constraint="uq_paints_brand_range_name",
        set_={
            "code": excluded.code,
            "hex": excluded.hex,
            "paint_type": excluded.paint_type,
            "finish": excluded.finish,
            "lab_l": excluded.lab_l,
            "lab_a": excluded.lab_a,
            "lab_b": excluded.lab_b,
            "is_active": excluded.is_active,
        },
    )

    try:
        await session.execute(statement)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    created = sum(
        1 for seed in CATALOG if (seed.brand, seed.range_name, seed.name) not in existing
    )
    return SeedResult(total=len(rows), created=created, updated=len(rows) - created)
