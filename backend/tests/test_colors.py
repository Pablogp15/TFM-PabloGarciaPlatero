"""Pruebas de la conversión de color y de la distancia CIELAB."""

from __future__ import annotations

import math

import pytest

from app.services.colors import (
    ColorError,
    hex_to_lab,
    hex_to_rgb,
    lab_distance,
    normalize_hex,
)


def test_normalize_hex_accepts_optional_hash_and_uppercases() -> None:
    assert normalize_hex("#aabbcc") == "#AABBCC"
    assert normalize_hex("aabbcc") == "#AABBCC"
    assert normalize_hex("  #00ff7f  ") == "#00FF7F"


def test_hex_to_rgb() -> None:
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("#00FF00") == (0, 255, 0)
    assert hex_to_rgb("#0000FF") == (0, 0, 255)


@pytest.mark.parametrize("value", ["", "#12345", "#GGGGGG", "rojo", "#1234567"])
def test_invalid_hex_values_are_rejected(value: str) -> None:
    with pytest.raises(ColorError):
        normalize_hex(value)


def test_white_is_the_lightness_reference() -> None:
    lightness, a_axis, b_axis = hex_to_lab("#FFFFFF")

    assert lightness == pytest.approx(100, abs=0.01)
    assert a_axis == pytest.approx(0, abs=0.01)
    assert b_axis == pytest.approx(0, abs=0.01)


def test_black_has_no_lightness() -> None:
    assert hex_to_lab("#000000") == (0.0, 0.0, 0.0)


def test_pure_red_matches_reference_values() -> None:
    lightness, a_axis, b_axis = hex_to_lab("#FF0000")

    assert lightness == pytest.approx(53.2408, abs=0.01)
    assert a_axis == pytest.approx(80.0925, abs=0.01)
    assert b_axis == pytest.approx(67.2032, abs=0.01)


def test_pure_blue_matches_reference_values() -> None:
    lightness, a_axis, b_axis = hex_to_lab("#0000FF")

    assert lightness == pytest.approx(32.2970, abs=0.01)
    assert a_axis == pytest.approx(79.1875, abs=0.01)
    assert b_axis == pytest.approx(-107.8602, abs=0.01)


def test_distance_is_zero_for_the_same_color() -> None:
    color = hex_to_lab("#A31621")
    assert lab_distance(color, color) == pytest.approx(0)


def test_distance_between_black_and_white_is_one_hundred() -> None:
    assert lab_distance(hex_to_lab("#000000"), hex_to_lab("#FFFFFF")) == pytest.approx(100)


def test_distance_is_symmetric() -> None:
    first = hex_to_lab("#A31621")
    second = hex_to_lab("#1F3A8F")

    assert lab_distance(first, second) == pytest.approx(lab_distance(second, first))
    assert math.isfinite(lab_distance(first, second))
