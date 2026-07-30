import sqlite3

from app.db import connection as connection_module


def test_get_connection_uses_delete_journal_mode(tmp_path, monkeypatch):
    """DELETE (no WAL) para que pae.db sea siempre el único archivo con la
    verdad completa -- el programa se distribuye copiando data/ a mano entre
    computadoras, y WAL puede dejar cambios recientes fuera de pae.db si no
    se copian también pae.db-wal/pae.db-shm."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    try:
        conn = connection_module.get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "delete"
    finally:
        connection_module._connection = None


def test_existing_wal_database_is_converted_on_open(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy_wal.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None

    # Simula una base creada por una versión anterior del programa, en modo WAL.
    setup_conn = sqlite3.connect(str(db_file))
    setup_conn.execute("PRAGMA journal_mode = WAL")
    setup_conn.execute("CREATE TABLE t (id INTEGER)")
    setup_conn.execute("INSERT INTO t VALUES (1)")
    setup_conn.commit()
    mode_while_open = setup_conn.execute("PRAGMA journal_mode").fetchone()[0]
    setup_conn.close()

    assert mode_while_open.lower() == "wal"

    try:
        conn = connection_module.get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "delete"
        assert conn.execute("SELECT id FROM t").fetchone()[0] == 1
    finally:
        connection_module._connection = None
