"""Inicialización y migración simple del esquema, controlada por schema_version."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CURRENT_VERSION = 14

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
    10: [
        # UUID + hash del documento (mismo identificador que trae el PDF
        # exportado -- ver app/pdf_io/requerimientos_pdf.py). En
        # requerimiento_batches se guardan de los DOS lados del intercambio:
        # lo que el Agente exportó/el Abogado importó, y lo que el Abogado
        # exportó de vuelta -- cada máquina llena las columnas que le tocan
        # (al exportar, directo; al importar, leyendo el UUID embebido en el
        # .mcdiep y recalculando el hash de los bytes recibidos).
        "ALTER TABLE requerimiento_batches ADD COLUMN agente_export_uuid TEXT",
        "ALTER TABLE requerimiento_batches ADD COLUMN agente_export_hash TEXT",
        "ALTER TABLE requerimiento_batches ADD COLUMN abogado_export_uuid TEXT",
        "ALTER TABLE requerimiento_batches ADD COLUMN abogado_export_hash TEXT",
        "ALTER TABLE revision_imports ADD COLUMN imported_uuid TEXT",
        "ALTER TABLE revision_imports ADD COLUMN imported_hash TEXT",
        # SQLite no permite modificar un CHECK existente con ALTER TABLE --
        # hay que reconstruir la tabla. Hace falta porque "HOJA DE CAMPO" se
        # agregó como tercera opción de recibe_citatorio/quien_recibe pero el
        # CHECK original (creado en versiones anteriores del esquema) sólo
        # permitía 'EN PUERTA'/'NOMBRE'; sin este ajuste, guardar esa opción
        # fallaría con un error de integridad en instalaciones existentes.
        """CREATE TABLE requerimiento_rows_v10 (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id                 INTEGER NOT NULL REFERENCES requerimiento_batches(id),
            folio                    TEXT,
            cta_predial              TEXT,
            contribuyente            TEXT,
            domicilio                TEXT,
            fecha_citatorio          TEXT,
            recibe_citatorio         TEXT CHECK (recibe_citatorio IN ('EN PUERTA', 'NOMBRE', 'HOJA DE CAMPO')),
            recibe_citatorio_nombre  TEXT,
            fecha_notificacion       TEXT,
            quien_recibe             TEXT CHECK (quien_recibe IN ('EN PUERTA', 'NOMBRE', 'HOJA DE CAMPO')),
            quien_recibe_nombre      TEXT,
            captured_at              TEXT
        )""",
        """INSERT INTO requerimiento_rows_v10
            SELECT id, batch_id, folio, cta_predial, contribuyente, domicilio,
                   fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre,
                   fecha_notificacion, quien_recibe, quien_recibe_nombre, captured_at
            FROM requerimiento_rows""",
        "DROP TABLE requerimiento_rows",
        "ALTER TABLE requerimiento_rows_v10 RENAME TO requerimiento_rows",
    ],
    11: [
        # Módulo de Mandamiento: mismo flujo que Requerimiento, en tablas
        # separadas (su Excel de origen no trae DOMICILIO -- sólo columnas
        # B, C y D -- y mezclar los lotes rompería la llave foránea de
        # imported_files.batch_id hacia requerimiento_batches).
        """CREATE TABLE IF NOT EXISTS mandamiento_batches (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            abogado_id            INTEGER NOT NULL REFERENCES users(id),
            agente_id             INTEGER NOT NULL REFERENCES users(id),
            status                TEXT NOT NULL DEFAULT 'PENDIENTE_ABOGADO'
                                  CHECK (status IN ('PENDIENTE_ABOGADO', 'CAPTURADO', 'EXPORTADO')),
            exported_agente_path  TEXT,
            exported_abogado_path TEXT,
            finalizado            INTEGER NOT NULL DEFAULT 0,
            agente_export_uuid    TEXT,
            agente_export_hash    TEXT,
            abogado_export_uuid   TEXT,
            abogado_export_hash   TEXT,
            created_at            TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS mandamiento_rows (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id                 INTEGER NOT NULL REFERENCES mandamiento_batches(id),
            folio                    TEXT,
            cta_predial              TEXT,
            contribuyente            TEXT,
            fecha_citatorio          TEXT,
            recibe_citatorio         TEXT CHECK (recibe_citatorio IN ('EN PUERTA', 'NOMBRE', 'HOJA DE CAMPO')),
            recibe_citatorio_nombre  TEXT,
            fecha_notificacion       TEXT,
            quien_recibe             TEXT CHECK (quien_recibe IN ('EN PUERTA', 'NOMBRE', 'HOJA DE CAMPO')),
            quien_recibe_nombre      TEXT,
            captured_at              TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS mandamiento_imported_files (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            agente_id         INTEGER NOT NULL REFERENCES users(id),
            abogado_id        INTEGER NOT NULL REFERENCES users(id),
            batch_id          INTEGER REFERENCES mandamiento_batches(id),
            row_count         INTEGER NOT NULL DEFAULT 0,
            imported_at       TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS mandamiento_revision_imports (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_id         INTEGER NOT NULL REFERENCES users(id),
            source_filename   TEXT NOT NULL,
            abogado_nombre    TEXT,
            abogado_id        INTEGER REFERENCES users(id),
            status            TEXT NOT NULL DEFAULT 'EN_REVISION'
                              CHECK (status IN ('EN_REVISION', 'PENDIENTE_REPORTE', 'REPORTE_ENVIADO')),
            status_changed_at TEXT NOT NULL DEFAULT (datetime('now')),
            imported_at       TEXT NOT NULL DEFAULT (datetime('now')),
            imported_uuid     TEXT,
            imported_hash     TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS mandamiento_revision_rows (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_id                INTEGER NOT NULL REFERENCES users(id),
            revision_import_id       INTEGER REFERENCES mandamiento_revision_imports(id),
            source_filename          TEXT NOT NULL,
            abogado_nombre           TEXT,
            abogado_id               INTEGER REFERENCES users(id),
            folio                    TEXT,
            cta_predial              TEXT,
            contribuyente            TEXT,
            fecha_citatorio          TEXT,
            recibe_citatorio         TEXT,
            recibe_citatorio_nombre  TEXT,
            fecha_notificacion       TEXT,
            quien_recibe             TEXT,
            quien_recibe_nombre      TEXT,
            procede                  TEXT CHECK (procede IN ('PROCEDE', 'NO PROCEDE')),
            imported_at              TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mandamiento_imported_files_agente ON mandamiento_imported_files(agente_id, original_filename)",
        "CREATE INDEX IF NOT EXISTS idx_mandamiento_batches_abogado ON mandamiento_batches(abogado_id)",
        "CREATE INDEX IF NOT EXISTS idx_mandamiento_rows_batch ON mandamiento_rows(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_mandamiento_revision_rows_agente ON mandamiento_revision_rows(agente_id)",
        "CREATE INDEX IF NOT EXISTS idx_mandamiento_revision_imports_agente ON mandamiento_revision_imports(agente_id)",
    ],
    12: [
        # Ruta completa (no sólo el nombre) del archivo tal como estaba en el
        # equipo al momento de cargarlo -- la usa el botón "Abrir ubicación
        # del archivo" del menú Histórico para reabrir el Explorador de
        # Windows justo ahí. Los registros previos a esta migración quedan
        # con original_path NULL (no se puede reconstruir esa ruta después).
        "ALTER TABLE imported_files ADD COLUMN original_path TEXT",
        "ALTER TABLE mandamiento_imported_files ADD COLUMN original_path TEXT",
    ],
    13: [
        # Nuevo rol REPORTEADOR (concentra en un solo "reporte general" lo
        # que el Agente genera y lo que el Abogado captura, por FOLIO) --
        # SQLite no permite modificar un CHECK existente con ALTER TABLE,
        # así que se reconstruye `users` igual que se hizo con
        # `requerimiento_rows` en la migración v10. A diferencia de aquella,
        # `users` SÍ es referenciada por FK desde muchas otras tablas
        # (batches, imported_files, revision_rows, etc.) -- con
        # `foreign_keys = ON` (activado por get_connection(), ver
        # app/db/connection.py), reconstruirla a mitad de esas referencias
        # falla con IntegrityError; se desactiva la verificación sólo
        # mientras dura este bloque y se reactiva al final.
        "PRAGMA foreign_keys = OFF",
        """CREATE TABLE users_v13 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT NOT NULL UNIQUE,
            role            TEXT NOT NULL CHECK (role IN ('SUPERUSUARIO', 'ADMINISTRADOR', 'AGENTE_PAE', 'ABOGADO', 'REPORTEADOR')),
            full_name       TEXT NOT NULL,
            email           TEXT,
            auth_type       TEXT NOT NULL CHECK (auth_type IN ('CERTIFICADO', 'PASSWORD')),
            password_hash   TEXT,
            password_salt   TEXT,
            cert_public_pem TEXT,
            cert_serial     TEXT,
            cert_file_path  TEXT,
            recovery_code_hash TEXT,
            recovery_code_salt TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            active          INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """INSERT INTO users_v13
            SELECT id, username, role, full_name, email, auth_type, password_hash, password_salt,
                   cert_public_pem, cert_serial, cert_file_path, recovery_code_hash, recovery_code_salt,
                   must_change_password, active, created_at, updated_at
            FROM users""",
        "DROP TABLE users",
        "ALTER TABLE users_v13 RENAME TO users",
        "PRAGMA foreign_keys = ON",
        # Campo "Observaciones" que el Abogado captura junto con las demás
        # columnas de citatorio/notificación -- viaja hasta la revisión del
        # Agente y de ahí al reporte general del Reporteador.
        "ALTER TABLE requerimiento_rows ADD COLUMN observaciones TEXT",
        "ALTER TABLE mandamiento_rows ADD COLUMN observaciones TEXT",
        "ALTER TABLE revision_rows ADD COLUMN observaciones TEXT",
        "ALTER TABLE mandamiento_revision_rows ADD COLUMN observaciones TEXT",
        # Reporte general: una fila por FOLIO (llave única), concentrando
        # datos del archivo de origen (que el Reporteador importa
        # directamente) y de la revisión que el Agente exporta al terminar
        # "Revisar Formato" -- ver app/db/repositories/reporte_requerimientos.py.
        """CREATE TABLE IF NOT EXISTS reporte_requerimientos_rows (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_numero           TEXT,
            folio                  TEXT NOT NULL UNIQUE,
            cta_predial            TEXT,
            contribuyente          TEXT,
            domicilio_ubicacion    TEXT,
            domicilio_notificacion TEXT,
            adeudo                 TEXT,
            despacho               TEXT,
            fecha_impreso          TEXT,
            fecha_entrega          TEXT,
            fecha_recepcion        TEXT,
            fecha_citatorio        TEXT,
            quien_recibe_citatorio TEXT,
            fecha_diligencia       TEXT,
            con_quien_notifico     TEXT,
            observaciones_abogado  TEXT,
            observaciones_area     TEXT,
            fecha_extrajudicial    TEXT,
            motivo_suspension      TEXT,
            source_filename        TEXT,
            created_at             TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at             TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS reporte_mandamientos_rows (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_numero           TEXT,
            folio                  TEXT NOT NULL UNIQUE,
            cta_predial            TEXT,
            contribuyente          TEXT,
            adeudo                 TEXT,
            despacho               TEXT,
            fecha_impreso          TEXT,
            fecha_entrega          TEXT,
            fecha_recepcion        TEXT,
            fecha_citatorio        TEXT,
            quien_recibe_citatorio TEXT,
            fecha_diligencia       TEXT,
            con_quien_notifico     TEXT,
            observaciones_abogado  TEXT,
            observaciones_area     TEXT,
            fecha_extrajudicial    TEXT,
            motivo_suspension      TEXT,
            source_filename        TEXT,
            created_at             TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at             TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_reporte_requerimientos_folio ON reporte_requerimientos_rows(folio)",
        "CREATE INDEX IF NOT EXISTS idx_reporte_mandamientos_folio ON reporte_mandamientos_rows(folio)",
    ],
    14: [
        # Timestamp propio del momento de exportación -- created_at/updated_at
        # del lote no sirven porque se pisan con cambios posteriores (editar,
        # finalizar, reenviar). Lo llena set_batch_export_path() en
        # app/db/repositories/requerimientos.py y mandamientos.py, y lo
        # muestra el Histórico (pestañas "exportados").
        "ALTER TABLE requerimiento_batches ADD COLUMN agente_exported_at TEXT",
        "ALTER TABLE requerimiento_batches ADD COLUMN abogado_exported_at TEXT",
        "ALTER TABLE mandamiento_batches ADD COLUMN agente_exported_at TEXT",
        "ALTER TABLE mandamiento_batches ADD COLUMN abogado_exported_at TEXT",
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
