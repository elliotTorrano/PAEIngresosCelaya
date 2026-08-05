-- Esquema de la base de datos local del Sistema PAE.
-- Cada instalación (equipo) mantiene su propia copia aislada de esta base.

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
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
);

CREATE TABLE IF NOT EXISTS imported_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    original_path     TEXT,
    agente_id         INTEGER NOT NULL REFERENCES users(id),
    abogado_id        INTEGER NOT NULL REFERENCES users(id),
    batch_id          INTEGER REFERENCES requerimiento_batches(id),
    row_count         INTEGER NOT NULL DEFAULT 0,
    imported_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS requerimiento_batches (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    abogado_id            INTEGER NOT NULL REFERENCES users(id),
    agente_id             INTEGER NOT NULL REFERENCES users(id),
    status                TEXT NOT NULL DEFAULT 'PENDIENTE_ABOGADO'
                          CHECK (status IN ('PENDIENTE_ABOGADO', 'CAPTURADO', 'EXPORTADO')),
    exported_agente_path  TEXT,
    exported_abogado_path TEXT,
    finalizado            INTEGER NOT NULL DEFAULT 0,
    -- Identificador del documento (UUID + hash, el mismo que trae el PDF
    -- exportado -- ver app/pdf_io/requerimientos_pdf.py). Cada máquina llena
    -- las columnas que le tocan: al exportar, directo; al importar, leyendo
    -- el UUID embebido en el .mcdiep y recalculando el hash de los bytes.
    agente_export_uuid    TEXT,
    agente_export_hash    TEXT,
    abogado_export_uuid   TEXT,
    abogado_export_hash   TEXT,
    -- Momento exacto de cada exportación real -- ver set_batch_export_path()
    -- en app/db/repositories/requerimientos.py. created_at/updated_at no
    -- sirven para esto porque updated_at se pisa con cambios posteriores.
    agente_exported_at    TEXT,
    abogado_exported_at   TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS requerimiento_rows (
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
    observaciones            TEXT,
    captured_at              TEXT
);

CREATE TABLE IF NOT EXISTS revision_imports (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    agente_id         INTEGER NOT NULL REFERENCES users(id),
    source_filename   TEXT NOT NULL,
    abogado_nombre    TEXT,
    abogado_id        INTEGER REFERENCES users(id),
    -- EN_REVISION: falta marcar PROCEDE/NO PROCEDE en alguna fila.
    -- PENDIENTE_REPORTE: todas las filas ya se marcaron, falta enviarlo como reporte.
    -- REPORTE_ENVIADO: ya se envió como reporte -- estado final, no se revierte solo.
    status            TEXT NOT NULL DEFAULT 'EN_REVISION'
                      CHECK (status IN ('EN_REVISION', 'PENDIENTE_REPORTE', 'REPORTE_ENVIADO')),
    status_changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    imported_at       TEXT NOT NULL DEFAULT (datetime('now')),
    -- Identificador del documento importado (UUID embebido en el .mcdiep +
    -- hash recalculado de los bytes recibidos), para comparar contra el PDF físico.
    imported_uuid     TEXT,
    imported_hash     TEXT
);

CREATE TABLE IF NOT EXISTS revision_rows (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    agente_id                INTEGER NOT NULL REFERENCES users(id),
    revision_import_id       INTEGER REFERENCES revision_imports(id),
    source_filename          TEXT NOT NULL,
    abogado_nombre           TEXT,
    abogado_id               INTEGER REFERENCES users(id),
    folio                    TEXT,
    cta_predial              TEXT,
    contribuyente            TEXT,
    domicilio                TEXT,
    fecha_citatorio          TEXT,
    recibe_citatorio         TEXT,
    recibe_citatorio_nombre  TEXT,
    fecha_notificacion       TEXT,
    quien_recibe             TEXT,
    quien_recibe_nombre      TEXT,
    observaciones            TEXT,
    procede                  TEXT CHECK (procede IN ('PROCEDE', 'NO PROCEDE')),
    imported_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Mandamiento: mismo flujo que Requerimiento (arriba), en tablas separadas
-- porque su Excel de origen no trae DOMICILIO (sólo columnas B, C y D) y
-- porque imported_files.batch_id ya apunta a requerimiento_batches con
-- llave foránea -- mezclar los dos tipos de lote en las mismas tablas
-- rompería esa referencia.
CREATE TABLE IF NOT EXISTS mandamiento_batches (
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
    -- Momento exacto de cada exportación real -- ver set_batch_export_path()
    -- en app/db/repositories/mandamientos.py. created_at/updated_at no sirven
    -- para esto porque updated_at se pisa con cambios posteriores del lote.
    agente_exported_at    TEXT,
    abogado_exported_at   TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mandamiento_rows (
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
    observaciones            TEXT,
    captured_at              TEXT
);

CREATE TABLE IF NOT EXISTS mandamiento_imported_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    original_path     TEXT,
    agente_id         INTEGER NOT NULL REFERENCES users(id),
    abogado_id        INTEGER NOT NULL REFERENCES users(id),
    batch_id          INTEGER REFERENCES mandamiento_batches(id),
    row_count         INTEGER NOT NULL DEFAULT 0,
    imported_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mandamiento_revision_imports (
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
);

CREATE TABLE IF NOT EXISTS mandamiento_revision_rows (
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
    observaciones            TEXT,
    procede                  TEXT CHECK (procede IN ('PROCEDE', 'NO PROCEDE')),
    imported_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reporte_requerimientos_rows (
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
    fecha_entrega           TEXT,
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
);

CREATE TABLE IF NOT EXISTS reporte_mandamientos_rows (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    lista_numero           TEXT,
    folio                  TEXT NOT NULL UNIQUE,
    cta_predial            TEXT,
    contribuyente          TEXT,
    adeudo                 TEXT,
    despacho               TEXT,
    fecha_impreso          TEXT,
    fecha_entrega           TEXT,
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
);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS reset_requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          TEXT NOT NULL,
    role              TEXT NOT NULL,
    reason            TEXT NOT NULL,
    detail            TEXT,
    requested_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status            TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (status IN ('PENDIENTE', 'ATENDIDA')),
    request_file_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_imported_files_agente ON imported_files(agente_id, original_filename);
CREATE INDEX IF NOT EXISTS idx_batches_abogado ON requerimiento_batches(abogado_id);
CREATE INDEX IF NOT EXISTS idx_rows_batch ON requerimiento_rows(batch_id);
CREATE INDEX IF NOT EXISTS idx_revision_rows_agente ON revision_rows(agente_id);
CREATE INDEX IF NOT EXISTS idx_revision_imports_agente ON revision_imports(agente_id);

CREATE INDEX IF NOT EXISTS idx_mandamiento_imported_files_agente ON mandamiento_imported_files(agente_id, original_filename);
CREATE INDEX IF NOT EXISTS idx_mandamiento_batches_abogado ON mandamiento_batches(abogado_id);
CREATE INDEX IF NOT EXISTS idx_mandamiento_rows_batch ON mandamiento_rows(batch_id);
CREATE INDEX IF NOT EXISTS idx_mandamiento_revision_rows_agente ON mandamiento_revision_rows(agente_id);
CREATE INDEX IF NOT EXISTS idx_mandamiento_revision_imports_agente ON mandamiento_revision_imports(agente_id);

CREATE INDEX IF NOT EXISTS idx_reporte_requerimientos_folio ON reporte_requerimientos_rows(folio);
CREATE INDEX IF NOT EXISTS idx_reporte_mandamientos_folio ON reporte_mandamientos_rows(folio);
