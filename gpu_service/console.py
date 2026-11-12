"""Compatibilidad de consola: fuerza UTF-8 en Windows.

DiffSynth imprime caracteres Unicode (por ejemplo ``[√]``) que la consola
heredada de Windows (cp1252) no puede representar. Reconfigurar los flujos
evita que un simple mensaje informativo aborte la carga del modelo.
"""

from __future__ import annotations

import sys


def configure_utf8() -> None:
    """Reconfigura stdout y stderr sin fallar si no son flujos reales."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
