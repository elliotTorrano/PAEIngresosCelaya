"""Repositorio de solicitudes de cambio de contraseña/certificado."""

from __future__ import annotations

import sqlite3

from app.config import RESET_STATUS_ATENDIDA, RESET_STATUS_PENDIENTE
from app.db.connection import get_connection


def create(*, username: str, role: str, reason: str, detail: str | None, request_file_path: str | None) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO reset_requests (username, role, reason, detail, request_file_path, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, role, reason, detail, request_file_path, RESET_STATUS_PENDIENTE),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def list_pending() -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM reset_requests WHERE status = ? ORDER BY requested_at", (RESET_STATUS_PENDIENTE,)
    ).fetchall()


def mark_attended(request_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE reset_requests SET status = ? WHERE id = ?", (RESET_STATUS_ATENDIDA, request_id))
    conn.commit()
