"""Inicialización y migración simple del esquema, controlada por schema_version."""

from __future__ import annotations

from pathlib import Path

from app.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CURRENT_VERSION = 1


def ensure_schema() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))

    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,))
        conn.commit()
    # Futuras migraciones incrementales se agregarían aquí, comparando
    # row["version"] contra CURRENT_VERSION.
