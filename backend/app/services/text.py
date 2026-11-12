"""Utilidades de búsqueda textual."""

from __future__ import annotations


def escape_like(value: str) -> str:
    """Escapa los comodines de ``LIKE`` para tratarlos como texto literal.

    Las consultas siguen siendo parametrizadas; esto solo evita que un usuario
    pueda alterar el patrón de búsqueda con ``%`` o ``_``.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
