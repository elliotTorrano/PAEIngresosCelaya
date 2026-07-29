"""Inicialización y migración simple del esquema, controlada por schema_version."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CURRENT_VERSION = 2

# Migraciones incrementales para bases de datos creadas con una versión anterior
# del esquema. schema.sql ya crea las tablas nuevas "desde cero" con todo esto
# incluido, así que en instalaciones nuevas estas sentencias no tienen nada que
# hacer (se ignora el error de columna/tabla ya existente).
_MIGRATIONS: dict[int, str] = {
    2: "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0",
}


def ensure_schema() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))

    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,))
        conn.commit()
        return

    version = row["version"]
    for target_version in sorted(v for v in _MIGRATIONS if v > version):
        try:
            conn.execute(_MIGRATIONS[target_version])
        except sqlite3.OperationalError:
            pass  # ya aplicada (p. ej. columna ya presente en una instalación nueva)
        conn.execute("UPDATE schema_version SET version = ?", (target_version,))
        conn.commit()
        version = target_version
