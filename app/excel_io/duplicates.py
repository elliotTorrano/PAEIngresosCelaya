"""Detección de archivos duplicados (mismo nombre) antes de copiar filas."""

from __future__ import annotations

from pathlib import Path

from app.db.repositories.requerimientos import filename_already_imported


def find_duplicate_filenames(agente_id: int, paths: list[Path]) -> list[str]:
    """Nombres de archivo ya importados antes por este agente, o repetidos dentro
    de la selección actual."""
    duplicates: list[str] = []
    seen_in_selection: set[str] = set()
    for path in paths:
        name = path.name
        if name in seen_in_selection or filename_already_imported(agente_id, name):
            duplicates.append(name)
        seen_in_selection.add(name)
    return duplicates
