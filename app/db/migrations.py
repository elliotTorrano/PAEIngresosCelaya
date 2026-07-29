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
    pending = sorted(v for v in _MIGRATIONS if v > version)
    if not pending:
        return

    _backup_before_migration(conn, version)

    for target_version in pending:
        try:
            conn.execute(_MIGRATIONS[target_version])
        except sqlite3.OperationalError:
            pass  # ya aplicada (p. ej. columna ya presente en una instalación nueva)
        conn.execute("UPDATE schema_version SET version = ?", (target_version,))
        conn.commit()
        version = target_version


def _backup_before_migration(conn: sqlite3.Connection, current_version: int) -> None:
    """Copia pae.db a pae.db.bak-vN (N = versión ANTES de migrar) por si una
    migración falla o daña datos. No sobrescribe un respaldo que ya exista
    para esa versión (no vuelve a respaldar en cada arranque, sólo la primera
    vez que se detectan migraciones pendientes desde esa versión)."""
    from app.db import connection as connection_module

    db_file = connection_module.db_path()
    if not db_file.exists():
        return  # base en memoria o inexistente (p. ej. en pruebas): nada que respaldar

    backup_path = db_file.with_name(f"{db_file.stem}.bak-v{current_version}{db_file.suffix}")
    if backup_path.exists():
        return

    backup_conn = sqlite3.connect(str(backup_path))
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()
