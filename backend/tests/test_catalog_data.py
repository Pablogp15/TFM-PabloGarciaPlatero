"""Validación del catálogo inicial empaquetado con la aplicación."""

from __future__ import annotations

import re

from app.data.paints_catalog import BRANDS, CATALOG
from app.models.enums import FinishType, PaintType
from app.services.colors import hex_to_lab, normalize_hex

HEX_PATTERN = re.compile(r"^#[0-9A-F]{6}$")


def test_catalog_has_a_representative_size() -> None:
    assert len(CATALOG) >= 100


def test_catalog_contains_the_three_supported_brands() -> None:
    assert {seed.brand for seed in CATALOG} == set(BRANDS)


def test_every_brand_has_several_paints() -> None:
    counts = {brand: sum(1 for seed in CATALOG if seed.brand == brand) for brand in BRANDS}

    assert all(count >= 20 for count in counts.values())


def test_natural_keys_are_unique() -> None:
    keys = [(seed.brand, seed.range_name, seed.name) for seed in CATALOG]

    assert len(keys) == len(set(keys))


def test_codes_are_unique_within_a_brand_and_range() -> None:
    coded = [
        (seed.brand, seed.range_name, seed.code)
        for seed in CATALOG
        if seed.code is not None
    ]

    assert len(coded) == len(set(coded))


def test_every_hex_is_valid_and_normalized() -> None:
    for seed in CATALOG:
        assert HEX_PATTERN.match(seed.hex), seed
        assert seed.hex == normalize_hex(seed.hex)


def test_every_paint_has_valid_lab_coordinates() -> None:
    for seed in CATALOG:
        lightness, a_axis, b_axis = hex_to_lab(seed.hex)
        assert 0 <= lightness <= 100
        assert -128 <= a_axis <= 127
        assert -128 <= b_axis <= 127


def test_catalog_covers_the_main_paint_types() -> None:
    paint_types = {seed.paint_type for seed in CATALOG}
    finishes = {seed.finish for seed in CATALOG}

    assert {
        PaintType.BASE,
        PaintType.LAYER,
        PaintType.WASH,
        PaintType.CONTRAST,
        PaintType.METALLIC,
        PaintType.TECHNICAL,
        PaintType.INK,
    } <= paint_types
    assert {FinishType.MATTE, FinishType.SATIN, FinishType.GLOSS} <= finishes
