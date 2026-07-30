"""Detección de archivos duplicados (mismo nombre) antes de copiar filas.

Sólo importa la duplicidad dentro del lote que se está preparando en este
momento para un abogado (la selección actual, o archivos ya agregados a ese
lote sin exportar todavía). El mismo nombre de archivo puede volver a
importarse más adelante (otro mes, otra corrección) sin ningún problema --
para eso queda el histórico completo en imported_files, que nunca bloquea.
"""

from __future__ import annotations

from pathlib import Path


def find_duplicate_filenames(paths: list[Path], already_in_batch: set[str] | None = None) -> list[str]:
    """Nombres de archivo repetidos dentro de `paths`, o que ya se habían
    agregado a este mismo lote (`already_in_batch`) antes de exportar."""
    seen: set[str] = set(already_in_batch or ())
    duplicates: list[str] = []
    for path in paths:
        name = path.name
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    return duplicates
