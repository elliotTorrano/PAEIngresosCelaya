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
