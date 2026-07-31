"""Inicialización y migración simple del esquema, controlada por schema_version."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CURRENT_VERSION = 9

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
    4: [
        "ALTER TABLE users ADD COLUMN recovery_code_hash TEXT",
        "ALTER TABLE users ADD COLUMN recovery_code_salt TEXT",
    ],
    5: "ALTER TABLE users ADD COLUMN cert_file_path TEXT",
    6: "ALTER TABLE requerimiento_batches ADD COLUMN finalizado INTEGER NOT NULL DEFAULT 0",
    7: "ALTER TABLE revision_rows ADD COLUMN abogado_id INTEGER REFERENCES users(id)",
    8: [
        # Antes, todas las filas importadas para revisión (de cualquier
        # archivo, en cualquier momento) se mostraban juntas en una sola
        # tabla -- al importar un segundo archivo, sus filas se "concatenaban"
        # con las del primero en vez de verse por separado. `revision_imports`
        # agrupa cada importación como un evento propio (como ya hace
        # `requerimiento_batches` con los lotes), para poder mostrar y filtrar
        # sólo el archivo que se está revisando en cada momento.
        """CREATE TABLE IF NOT EXISTS revision_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_id INTEGER NOT NULL REFERENCES users(id),
            source_filename TEXT NOT NULL,
            abogado_nombre TEXT,
            abogado_id INTEGER REFERENCES users(id),
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_revision_imports_agente ON revision_imports(agente_id)",
        "ALTER TABLE revision_rows ADD COLUMN revision_import_id INTEGER REFERENCES revision_imports(id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_rows_import ON revision_rows(revision_import_id)",
        # Reconstruye un revision_imports por cada importación pasada,
        # agrupando por (agente, archivo, abogado, fecha/hora exacta de
        # importación) -- todas las filas de una misma llamada a
        # add_revision_rows() comparten ese mismo datetime('now').
        """INSERT INTO revision_imports (agente_id, source_filename, abogado_nombre, abogado_id, imported_at)
            SELECT DISTINCT agente_id, source_filename, abogado_nombre, abogado_id, imported_at
            FROM revision_rows
            WHERE revision_import_id IS NULL""",
        """UPDATE revision_rows
            SET revision_import_id = (
                SELECT ri.id FROM revision_imports ri
                WHERE ri.agente_id = revision_rows.agente_id
                  AND ri.source_filename = revision_rows.source_filename
                  AND ri.imported_at = revision_rows.imported_at
                  AND ri.abogado_id IS revision_rows.abogado_id
                ORDER BY ri.id DESC
                LIMIT 1
            )
            WHERE revision_import_id IS NULL""",
    ],
    9: [
        # Estado explícito por archivo importado (antes sólo se sabía si
        # estaba "revisado" o no, calculado al vuelo) -- lo usa el nuevo
        # menú "Seguimiento" del Agente para distinguir lo que falta
        # revisar, lo revisado que falta enviar como reporte, y lo ya
        # enviado (este último, terminal: no se recalcula solo).
        "ALTER TABLE revision_imports ADD COLUMN status TEXT NOT NULL DEFAULT 'EN_REVISION'",
        "ALTER TABLE revision_imports ADD COLUMN status_changed_at TEXT",
        "UPDATE revision_imports SET status_changed_at = imported_at WHERE status_changed_at IS NULL",
        # Recalcula el estado real de lo que ya estaba 100% revisado antes
        # de esta migración (bajo el esquema viejo, sólo existía el
        # concepto "revisado" calculado; ahora hay que fijarlo).
        """UPDATE revision_imports
            SET status = 'PENDIENTE_REPORTE'
            WHERE id IN (
                SELECT ri.id FROM revision_imports ri
                JOIN revision_rows rr ON rr.revision_import_id = ri.id
                GROUP BY ri.id
                HAVING COUNT(rr.id) > 0
                   AND SUM(CASE WHEN rr.procede IS NOT NULL THEN 1 ELSE 0 END) = COUNT(rr.id)
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
