"""Nombres de archivo seguros en Windows, compartido por los flujos de
exportación (Agente, Abogado, Seguimiento) y por app/pdf_io."""

from __future__ import annotations

import re

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename(text: str) -> str:
    """Reemplaza caracteres inválidos en nombres de archivo de Windows por '_'."""
    return _INVALID_FILENAME_CHARS.sub("_", text).strip()
