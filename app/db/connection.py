"""Conexión sqlite3 compartida para toda la app (una sola base local por instalación).

Se usa el modo de bitácora DELETE (el predeterminado de SQLite) a propósito, en
vez de WAL: WAL guarda cambios recientes en archivos adicionales (pae.db-wal,
pae.db-shm) aparte del archivo principal, y este programa se distribuye
literalmente copiando la carpeta data/ de una computadora a otra -- si alguien
copia sólo pae.db sin esos archivos adicionales (o copia mientras el programa
sigue abierto), la copia puede quedar con datos incompletos o desactualizados.
Con DELETE, pae.db es siempre el único archivo con la verdad completa en cuanto
termina cada operación.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from app.utils.paths import db_path

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(db_path()), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
        # Si la base ya estaba en modo WAL (versiones anteriores del programa),
        # este cambio la convierte de vuelta y consolida cualquier pendiente
        # en pae.db-wal hacia el archivo principal.
        _connection.execute("PRAGMA journal_mode = DELETE")
    return _connection


@contextmanager
def transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
