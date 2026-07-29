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
