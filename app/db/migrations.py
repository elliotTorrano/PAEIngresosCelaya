"""Inicialización y migración simple del esquema, controlada por schema_version."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CURRENT_VERSION = 3

# Migraciones incrementales para bases de datos creadas con una versión anterior
# del esquema. schema.sql ya crea las tablas nuevas "desde cero" con todo esto
# incluido, así que en instalaciones nuevas estas sentencias no tienen nada que
# hacer (se ignora el error de columna/tabla ya existente).
# Cada valor puede ser un solo string SQL, o una lista de strings si la versión
# necesita varias sentencias (ALTER TABLE sólo admite una columna a la vez).
_MIGRATIONS: dict[int, str | list[str]] = {
    2: "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0",
    3: [
        "ALTER TABLE requerimiento_rows ADD COLUMN fecha_citatorio TEXT",
        "ALTER TABLE requerimiento_rows ADD COLUMN recibe_citatorio TEXT",
        "ALTER TABLE requerimiento_rows ADD COLUMN recibe_citatorio_nombre TEXT",
        """CREATE TABLE IF NOT EXISTS revision_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_id INTEGER NOT NULL REFERENCES users(id),
            source_filename TEXT NOT NULL,
            abogado_nombre TEXT,
            folio TEXT, cta_predial TEXT, contribuyente TEXT, domicilio TEXT,
            fecha_citatorio TEXT, recibe_citatorio TEXT, recibe_citatorio_nombre TEXT,
            fecha_notificacion TEXT, quien_recibe TEXT, quien_recibe_nombre TEXT,
            procede TEXT CHECK (procede IN ('PROCEDE', 'NO PROCEDE')),
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ],
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
        statements = _MIGRATIONS[target_version]
        if isinstance(statements, str):
            statements = [statements]
        for statement in statements:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError:
                pass  # ya aplicada (p. ej. columna/tabla ya presente en una instalación nueva)
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
