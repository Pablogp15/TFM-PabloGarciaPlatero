"""Conversión de colores sRGB a CIELAB y distancia entre colores.

El catálogo guarda las coordenadas Lab para poder buscar pinturas de tono
parecido sin depender de comparaciones RGB, que no se corresponden con la
percepción humana.
"""

from __future__ import annotations

import math
import re

_HEX_PATTERN = re.compile(r"^#?([0-9A-Fa-f]{6})$")

# Blanco de referencia D65, el mismo que usan los perfiles sRGB.
_REFERENCE_WHITE = (0.95047, 1.0, 1.08883)
_EPSILON = (6 / 29) ** 3
_KAPPA = 3 * (6 / 29) ** 2


class ColorError(ValueError):
    """El valor recibido no es un color hexadecimal válido."""


def normalize_hex(value: str) -> str:
    """Devuelve el color en formato ``#RRGGBB``.

    Se acepta el valor con o sin almohadilla, pero siempre se devuelve en
    mayúsculas para que la representación sea única.
    """
    match = _HEX_PATTERN.match(value.strip())
    if match is None:
        raise ColorError("El color debe tener el formato #RRGGBB")
    return f"#{match.group(1).upper()}"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convierte ``#RRGGBB`` en una tupla de componentes 0-255."""
    normalized = normalize_hex(value)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def _srgb_to_linear(channel: int) -> float:
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return math.pow((value + 0.055) / 1.055, 2.4)


def _lab_component(value: float) -> float:
    if value > _EPSILON:
        return math.pow(value, 1 / 3)
    return value / _KAPPA + 4 / 29


def hex_to_lab(value: str) -> tuple[float, float, float]:
    """Convierte un color sRGB a CIELAB (iluminante D65).

    El resultado se redondea a cuatro decimales para ajustarse a la precisión
    de las columnas ``lab_l``, ``lab_a`` y ``lab_b``.
    """
    red, green, blue = (_srgb_to_linear(channel) for channel in hex_to_rgb(value))

    x = 0.4124564 * red + 0.3575761 * green + 0.1804375 * blue
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = 0.0193339 * red + 0.1191920 * green + 0.9503041 * blue

    fx = _lab_component(x / _REFERENCE_WHITE[0])
    fy = _lab_component(y / _REFERENCE_WHITE[1])
    fz = _lab_component(z / _REFERENCE_WHITE[2])

    lightness = 116 * fy - 16
    a_axis = 500 * (fx - fy)
    b_axis = 200 * (fy - fz)

    return (
        round(lightness, 4),
        round(a_axis, 4),
        round(b_axis, 4),
    )


def lab_distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    """Distancia euclídea entre dos colores en el espacio CIELAB."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second, strict=True)))
