import sqlite3

from app.db import connection as connection_module
from app.db.migrations import CURRENT_VERSION, ensure_schema


def test_migration_adds_must_change_password_column(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada con el esquema v1 (sin la columna nueva).
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (1)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            auth_type TEXT NOT NULL,
            password_hash TEXT,
            password_salt TEXT,
            cert_public_pem TEXT,
            cert_serial TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        assert "must_change_password" in columns

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_creates_backup_before_altering(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Base v1 con un usuario real, para comprobar que el respaldo preserva los datos.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (1)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            auth_type TEXT NOT NULL,
            password_hash TEXT,
            password_salt TEXT,
            cert_public_pem TEXT,
            cert_serial TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (username, role, full_name, auth_type) VALUES ('pre_migracion', 'ABOGADO', 'Antes', 'PASSWORD')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        backup_path = tmp_path / "legacy.bak-v1.db"
        assert backup_path.exists()

        backup_conn = sqlite3.connect(str(backup_path))
        backup_conn.row_factory = sqlite3.Row
        try:
            columns = [row["name"] for row in backup_conn.execute("PRAGMA table_info(users)")]
            assert "must_change_password" not in columns  # foto de ANTES de migrar

            row = backup_conn.execute("SELECT * FROM users WHERE username = 'pre_migracion'").fetchone()
            assert row is not None
            assert row["full_name"] == "Antes"
        finally:
            backup_conn.close()

        # La base viva sí quedó migrada.
        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        assert "must_change_password" in columns

        # Una segunda "ejecución" (ya en v2, sin migraciones pendientes) no debe
        # generar respaldos adicionales.
        ensure_schema()
        assert not (tmp_path / "legacy.bak-v2.db").exists()
    finally:
        connection_module._connection = None


def test_migration_v3_adds_citatorio_columns_and_revision_rows_table(tmp_path, monkeypatch):
    db_file = tmp_path / "v2.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada con el esquema v2: requerimiento_rows en su forma
    # ANTERIOR (sin las columnas de citatorio), y sin la tabla revision_rows.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (2)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE requerimiento_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, abogado_id INTEGER NOT NULL, agente_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDIENTE_ABOGADO',
            exported_agente_path TEXT, exported_abogado_path TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE requerimiento_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id INTEGER NOT NULL,
            folio TEXT, cta_predial TEXT, contribuyente TEXT, domicilio TEXT,
            fecha_notificacion TEXT, quien_recibe TEXT, quien_recibe_nombre TEXT, captured_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO requerimiento_batches (id, abogado_id, agente_id) VALUES (1, 1, 1)"
    )
    conn.execute(
        "INSERT INTO requerimiento_rows (batch_id, folio) VALUES (1, 'F-001')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(requerimiento_rows)")]
        assert "fecha_citatorio" in columns
        assert "recibe_citatorio" in columns
        assert "recibe_citatorio_nombre" in columns

        # El dato preexistente se conserva.
        row = conn.execute("SELECT folio FROM requerimiento_rows WHERE batch_id = 1").fetchone()
        assert row["folio"] == "F-001"

        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "revision_rows" in tables

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v4_adds_recovery_code_columns(tmp_path, monkeypatch):
    db_file = tmp_path / "v3.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada con el esquema v3: users sin las columnas de código de respaldo.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (3)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (username, role, full_name, auth_type) VALUES ('admin', 'ADMINISTRADOR', 'Admin', 'CERTIFICADO')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        assert "recovery_code_hash" in columns
        assert "recovery_code_salt" in columns

        row = conn.execute("SELECT full_name FROM users WHERE username = 'admin'").fetchone()
        assert row["full_name"] == "Admin"

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v5_adds_cert_file_path_column(tmp_path, monkeypatch):
    db_file = tmp_path / "v4.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada con el esquema v4: users sin cert_file_path.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (4)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            recovery_code_hash TEXT, recovery_code_salt TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (username, role, full_name, auth_type) VALUES ('admin', 'ADMINISTRADOR', 'Admin', 'CERTIFICADO')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        assert "cert_file_path" in columns

        row = conn.execute("SELECT full_name FROM users WHERE username = 'admin'").fetchone()
        assert row["full_name"] == "Admin"

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v8_creates_revision_imports_and_backfills_existing_rows(tmp_path, monkeypatch):
    db_file = tmp_path / "v7.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada con el esquema v7: revision_rows en su forma
    # ANTERIOR (sin revision_import_id), con datos de dos importaciones
    # distintas ya guardados -- antes de esta migración, la pantalla de
    # revisión las mostraba todas juntas ("concatenadas").
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (7)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (id, username, role, full_name, auth_type) VALUES (1, 'agente1', 'AGENTE_PAE', 'Agente Uno', 'CERTIFICADO')"
    )
    conn.execute(
        """
        CREATE TABLE revision_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agente_id INTEGER NOT NULL,
            source_filename TEXT NOT NULL, abogado_nombre TEXT, abogado_id INTEGER,
            folio TEXT, cta_predial TEXT, contribuyente TEXT, domicilio TEXT,
            fecha_citatorio TEXT, recibe_citatorio TEXT, recibe_citatorio_nombre TEXT,
            fecha_notificacion TEXT, quien_recibe TEXT, quien_recibe_nombre TEXT,
            procede TEXT, imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO revision_rows (agente_id, source_filename, folio, imported_at) "
        "VALUES (1, 'lote1.xlsx', 'F-001', '2026-01-01 10:00:00')"
    )
    conn.execute(
        "INSERT INTO revision_rows (agente_id, source_filename, folio, imported_at) "
        "VALUES (1, 'lote2.xlsx', 'F-002', '2026-01-02 11:00:00')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "revision_imports" in tables

        imports = conn.execute("SELECT * FROM revision_imports ORDER BY source_filename").fetchall()
        assert len(imports) == 2
        assert {i["source_filename"] for i in imports} == {"lote1.xlsx", "lote2.xlsx"}

        rows = conn.execute("SELECT * FROM revision_rows ORDER BY folio").fetchall()
        assert all(r["revision_import_id"] is not None for r in rows)
        # Cada fila quedó ligada al import de SU propio archivo, no mezcladas.
        lote1_import_id = next(i["id"] for i in imports if i["source_filename"] == "lote1.xlsx")
        lote2_import_id = next(i["id"] for i in imports if i["source_filename"] == "lote2.xlsx")
        row_f001 = next(r for r in rows if r["folio"] == "F-001")
        row_f002 = next(r for r in rows if r["folio"] == "F-002")
        assert row_f001["revision_import_id"] == lote1_import_id
        assert row_f002["revision_import_id"] == lote2_import_id

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v10_adds_identity_columns_and_allows_hoja_de_campo(tmp_path, monkeypatch):
    db_file = tmp_path / "v9.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base v9: requerimiento_batches/requerimiento_rows sin las
    # columnas de identidad, y con el CHECK viejo (sólo EN PUERTA/NOMBRE,
    # sin HOJA DE CAMPO) -- así como quedaron instalaciones reales antes de
    # esta versión.
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (9)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (id, username, role, full_name, auth_type) VALUES (1, 'agente1', 'AGENTE_PAE', 'Agente Uno', 'CERTIFICADO')"
    )
    conn.execute(
        "INSERT INTO users (id, username, role, full_name, auth_type, password_hash, password_salt) "
        "VALUES (2, 'abogado1', 'ABOGADO', 'Abogado Uno', 'PASSWORD', 'x', 'y')"
    )
    conn.execute(
        """
        CREATE TABLE requerimiento_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abogado_id INTEGER NOT NULL REFERENCES users(id),
            agente_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'PENDIENTE_ABOGADO',
            exported_agente_path TEXT, exported_abogado_path TEXT,
            finalizado INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE requerimiento_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL REFERENCES requerimiento_batches(id),
            folio TEXT, cta_predial TEXT, contribuyente TEXT, domicilio TEXT,
            fecha_citatorio TEXT,
            recibe_citatorio TEXT CHECK (recibe_citatorio IN ('EN PUERTA', 'NOMBRE')),
            recibe_citatorio_nombre TEXT,
            fecha_notificacion TEXT,
            quien_recibe TEXT CHECK (quien_recibe IN ('EN PUERTA', 'NOMBRE')),
            quien_recibe_nombre TEXT,
            captured_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE revision_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agente_id INTEGER NOT NULL,
            source_filename TEXT NOT NULL, abogado_nombre TEXT, abogado_id INTEGER,
            status TEXT NOT NULL DEFAULT 'EN_REVISION', status_changed_at TEXT,
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO requerimiento_batches (id, abogado_id, agente_id) VALUES (1, 2, 1)"
    )
    conn.execute(
        "INSERT INTO requerimiento_rows (batch_id, folio, cta_predial, contribuyente, domicilio, "
        "recibe_citatorio, quien_recibe) VALUES (1, 'F-001', 'C-001', 'Fulano', 'Calle 1', 'EN PUERTA', 'NOMBRE')"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()

        # La fila que ya existía se preservó tal cual a través de la
        # reconstrucción de la tabla.
        row = conn.execute("SELECT * FROM requerimiento_rows WHERE batch_id = 1").fetchone()
        assert row["folio"] == "F-001"
        assert row["recibe_citatorio"] == "EN PUERTA"

        # El CHECK viejo ya no bloquea HOJA DE CAMPO.
        conn.execute(
            "INSERT INTO requerimiento_rows (batch_id, folio, recibe_citatorio, quien_recibe) "
            "VALUES (1, 'F-002', 'HOJA DE CAMPO', 'HOJA DE CAMPO')"
        )
        conn.commit()

        batches_columns = [r["name"] for r in conn.execute("PRAGMA table_info(requerimiento_batches)")]
        for col in ("agente_export_uuid", "agente_export_hash", "abogado_export_uuid", "abogado_export_hash"):
            assert col in batches_columns

        revision_columns = [r["name"] for r in conn.execute("PRAGMA table_info(revision_imports)")]
        assert "imported_uuid" in revision_columns
        assert "imported_hash" in revision_columns

        conn.execute(
            "UPDATE requerimiento_batches SET agente_export_uuid = 'u', agente_export_hash = 'h' WHERE id = 1"
        )
        conn.commit()
        updated = conn.execute("SELECT agente_export_uuid, agente_export_hash FROM requerimiento_batches WHERE id = 1").fetchone()
        assert updated["agente_export_uuid"] == "u"
        assert updated["agente_export_hash"] == "h"

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v9_adds_status_and_recomputes_fully_reviewed_imports(tmp_path, monkeypatch):
    db_file = tmp_path / "v8.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base v8: revision_imports sin status/status_changed_at, con
    # un import completamente revisado (bajo el esquema viejo, "revisado" era
    # sólo calculado) y otro a medias.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (8)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO users (id, username, role, full_name, auth_type) VALUES (1, 'agente1', 'AGENTE_PAE', 'Agente Uno', 'CERTIFICADO')"
    )
    conn.execute(
        """
        CREATE TABLE revision_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agente_id INTEGER NOT NULL,
            source_filename TEXT NOT NULL, abogado_nombre TEXT, abogado_id INTEGER,
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE revision_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agente_id INTEGER NOT NULL,
            revision_import_id INTEGER, source_filename TEXT NOT NULL,
            abogado_nombre TEXT, abogado_id INTEGER,
            folio TEXT, cta_predial TEXT, contribuyente TEXT, domicilio TEXT,
            fecha_citatorio TEXT, recibe_citatorio TEXT, recibe_citatorio_nombre TEXT,
            fecha_notificacion TEXT, quien_recibe TEXT, quien_recibe_nombre TEXT,
            procede TEXT, imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO revision_imports (id, agente_id, source_filename) VALUES (1, 1, 'completo.xlsx')"
    )
    conn.execute(
        "INSERT INTO revision_imports (id, agente_id, source_filename) VALUES (2, 1, 'a_medias.xlsx')"
    )
    conn.execute(
        "INSERT INTO revision_rows (agente_id, revision_import_id, source_filename, folio, procede) "
        "VALUES (1, 1, 'completo.xlsx', 'F-001', 'PROCEDE')"
    )
    conn.execute(
        "INSERT INTO revision_rows (agente_id, revision_import_id, source_filename, folio, procede) "
        "VALUES (1, 2, 'a_medias.xlsx', 'F-002', 'PROCEDE')"
    )
    conn.execute(
        "INSERT INTO revision_rows (agente_id, revision_import_id, source_filename, folio, procede) "
        "VALUES (1, 2, 'a_medias.xlsx', 'F-003', NULL)"
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(revision_imports)")]
        assert "status" in columns
        assert "status_changed_at" in columns

        completo = conn.execute("SELECT status FROM revision_imports WHERE id = 1").fetchone()
        assert completo["status"] == "PENDIENTE_REPORTE"

        a_medias = conn.execute("SELECT status FROM revision_imports WHERE id = 2").fetchone()
        assert a_medias["status"] == "EN_REVISION"

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_migration_v11_creates_mandamiento_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "v10.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base v10: sólo las tablas de Requerimiento, sin ninguna de
    # las de Mandamiento todavía.
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (10)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT, auth_type TEXT NOT NULL,
            password_hash TEXT, password_salt TEXT, cert_public_pem TEXT, cert_serial TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()

    try:
        ensure_schema()

        conn = connection_module.get_connection()
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for expected in (
            "mandamiento_batches", "mandamiento_rows", "mandamiento_imported_files",
            "mandamiento_revision_imports", "mandamiento_revision_rows",
        ):
            assert expected in tables

        columns = [row["name"] for row in conn.execute("PRAGMA table_info(mandamiento_rows)")]
        assert "domicilio" not in columns
        assert "folio" in columns

        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None


def test_fresh_schema_already_has_column(tmp_path, monkeypatch):
    db_file = tmp_path / "fresh.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    try:
        ensure_schema()
        conn = connection_module.get_connection()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        assert "must_change_password" in columns
        version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        assert version == CURRENT_VERSION
    finally:
        connection_module._connection = None
