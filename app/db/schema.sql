-- Esquema de la base de datos local del Sistema PAE.
-- Cada instalación (equipo) mantiene su propia copia aislada de esta base.

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL CHECK (role IN ('SUPERUSUARIO', 'ADMINISTRADOR', 'AGENTE_PAE', 'ABOGADO')),
    full_name       TEXT NOT NULL,
    email           TEXT,
    auth_type       TEXT NOT NULL CHECK (auth_type IN ('CERTIFICADO', 'PASSWORD')),
    password_hash   TEXT,
    password_salt   TEXT,
    cert_public_pem TEXT,
    cert_serial     TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS imported_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
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
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS requerimiento_rows (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            INTEGER NOT NULL REFERENCES requerimiento_batches(id),
    folio               TEXT,
    cta_predial         TEXT,
    contribuyente       TEXT,
    domicilio           TEXT,
    fecha_notificacion  TEXT,
    quien_recibe        TEXT CHECK (quien_recibe IN ('EN PUERTA', 'NOMBRE')),
    quien_recibe_nombre TEXT,
    captured_at         TEXT
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
