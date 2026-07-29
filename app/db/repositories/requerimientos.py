"""Repositorio del flujo de Formato de Requerimientos: lotes, filas y archivos importados."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.config import BATCH_STATUS_PENDIENTE_ABOGADO
from app.db.connection import get_connection


@dataclass
class RequerimientoRow:
    id: int
    batch_id: int
    folio: str | None
    cta_predial: str | None
    contribuyente: str | None
    domicilio: str | None
    fecha_notificacion: str | None
    quien_recibe: str | None
    quien_recibe_nombre: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RequerimientoRow":
        return cls(
            id=row["id"],
            batch_id=row["batch_id"],
            folio=row["folio"],
            cta_predial=row["cta_predial"],
            contribuyente=row["contribuyente"],
            domicilio=row["domicilio"],
            fecha_notificacion=row["fecha_notificacion"],
            quien_recibe=row["quien_recibe"],
            quien_recibe_nombre=row["quien_recibe_nombre"],
        )

    @property
    def is_captured(self) -> bool:
        return bool(self.fecha_notificacion) and bool(self.quien_recibe)


def create_batch(*, abogado_id: int, agente_id: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO requerimiento_batches (abogado_id, agente_id, status) VALUES (?, ?, ?)",
        (abogado_id, agente_id, BATCH_STATUS_PENDIENTE_ABOGADO),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def add_rows(batch_id: int, rows: list[dict]) -> None:
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO requerimiento_rows (batch_id, folio, cta_predial, contribuyente, domicilio)
        VALUES (:batch_id, :folio, :cta_predial, :contribuyente, :domicilio)
        """,
        [{**r, "batch_id": batch_id} for r in rows],
    )
    conn.commit()


def record_imported_file(
    *, original_filename: str, agente_id: int, abogado_id: int, batch_id: int, row_count: int
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO imported_files (original_filename, agente_id, abogado_id, batch_id, row_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (original_filename, agente_id, abogado_id, batch_id, row_count),
    )
    conn.commit()


def filename_already_imported(agente_id: int, filename: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM imported_files WHERE agente_id = ? AND original_filename = ?",
        (agente_id, filename),
    ).fetchone()
    return row is not None


def list_batches_for_abogado(abogado_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM requerimiento_batches WHERE abogado_id = ? ORDER BY created_at DESC",
        (abogado_id,),
    ).fetchall()


def get_batch(batch_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    return conn.execute("SELECT * FROM requerimiento_batches WHERE id = ?", (batch_id,)).fetchone()


def list_rows(batch_id: int) -> list[RequerimientoRow]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM requerimiento_rows WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    return [RequerimientoRow.from_row(r) for r in rows]


def update_row_capture(
    row_id: int, *, fecha_notificacion: str | None, quien_recibe: str | None, quien_recibe_nombre: str | None
) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE requerimiento_rows
        SET fecha_notificacion = ?, quien_recibe = ?, quien_recibe_nombre = ?, captured_at = datetime('now')
        WHERE id = ?
        """,
        (fecha_notificacion, quien_recibe, quien_recibe_nombre, row_id),
    )
    conn.commit()


def set_batch_status(batch_id: int, status: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE requerimiento_batches SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, batch_id),
    )
    conn.commit()


def set_batch_export_path(batch_id: int, *, agente_path: str | None = None, abogado_path: str | None = None) -> None:
    conn = get_connection()
    if agente_path is not None:
        conn.execute(
            "UPDATE requerimiento_batches SET exported_agente_path = ?, updated_at = datetime('now') WHERE id = ?",
            (agente_path, batch_id),
        )
    if abogado_path is not None:
        conn.execute(
            "UPDATE requerimiento_batches SET exported_abogado_path = ?, updated_at = datetime('now') WHERE id = ?",
            (abogado_path, batch_id),
        )
    conn.commit()
