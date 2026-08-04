"""Repositorio del flujo de Formato de Mandamientos: lotes, filas y archivos
importados. Mismo flujo que app/db/repositories/requerimientos.py, en tablas
separadas -- el Excel de origen de Mandamiento no trae DOMICILIO (sólo se
copian las columnas B, C y D)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.config import BATCH_STATUS_PENDIENTE_ABOGADO
from app.db.connection import get_connection


@dataclass
class MandamientoRow:
    id: int
    batch_id: int
    folio: str | None
    cta_predial: str | None
    contribuyente: str | None
    fecha_citatorio: str | None
    recibe_citatorio: str | None
    recibe_citatorio_nombre: str | None
    fecha_notificacion: str | None
    quien_recibe: str | None
    quien_recibe_nombre: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MandamientoRow":
        return cls(
            id=row["id"],
            batch_id=row["batch_id"],
            folio=row["folio"],
            cta_predial=row["cta_predial"],
            contribuyente=row["contribuyente"],
            fecha_citatorio=row["fecha_citatorio"],
            recibe_citatorio=row["recibe_citatorio"],
            recibe_citatorio_nombre=row["recibe_citatorio_nombre"],
            fecha_notificacion=row["fecha_notificacion"],
            quien_recibe=row["quien_recibe"],
            quien_recibe_nombre=row["quien_recibe_nombre"],
        )

    @property
    def is_captured(self) -> bool:
        return (
            bool(self.fecha_citatorio) and bool(self.recibe_citatorio)
            and bool(self.fecha_notificacion) and bool(self.quien_recibe)
        )

    @property
    def is_modified(self) -> bool:
        """True si el Abogado capturó algo en esta fila (aunque sea parcial).
        Se usa para excluir del export las filas que siguen exactamente como
        se importaron."""
        return any(
            (
                self.fecha_citatorio, self.recibe_citatorio, self.recibe_citatorio_nombre,
                self.fecha_notificacion, self.quien_recibe, self.quien_recibe_nombre,
            )
        )


def create_batch(*, abogado_id: int, agente_id: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO mandamiento_batches (abogado_id, agente_id, status) VALUES (?, ?, ?)",
        (abogado_id, agente_id, BATCH_STATUS_PENDIENTE_ABOGADO),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def add_rows(batch_id: int, rows: list[dict]) -> None:
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO mandamiento_rows (batch_id, folio, cta_predial, contribuyente)
        VALUES (:batch_id, :folio, :cta_predial, :contribuyente)
        """,
        [{**r, "batch_id": batch_id} for r in rows],
    )
    conn.commit()


def record_imported_file(
    *, original_filename: str, agente_id: int, abogado_id: int, row_count: int, batch_id: int | None = None,
    original_path: str | None = None,
) -> None:
    """Registra en el histórico que se subió un archivo (quién, cuándo, cuántas
    filas). No hay restricción de unicidad: el mismo nombre puede volver a
    aparecer tantas veces como se vuelva a subir, cada vez con su propia fecha.
    original_path es la ruta completa en el equipo de origen -- la usa el
    botón "Abrir ubicación del archivo" de Histórico."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO mandamiento_imported_files (original_filename, original_path, agente_id, abogado_id, batch_id, row_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (original_filename, original_path, agente_id, abogado_id, batch_id, row_count),
    )
    conn.commit()


def link_imported_files_to_batch(*, agente_id: int, filenames: list[str], batch_id: int) -> None:
    """Asocia con `batch_id` el registro de mandamiento_imported_files más
    reciente (sin lote asignado todavía) de cada nombre de archivo, al
    momento de exportar."""
    conn = get_connection()
    for filename in filenames:
        conn.execute(
            """
            UPDATE mandamiento_imported_files
            SET batch_id = ?
            WHERE id = (
                SELECT id FROM mandamiento_imported_files
                WHERE agente_id = ? AND original_filename = ? AND batch_id IS NULL
                ORDER BY imported_at DESC
                LIMIT 1
            )
            """,
            (batch_id, agente_id, filename),
        )
    conn.commit()


def list_batches_for_abogado(abogado_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM mandamiento_batches WHERE abogado_id = ? ORDER BY created_at DESC",
        (abogado_id,),
    ).fetchall()


def list_batches_for_agente(agente_id: int) -> list[sqlite3.Row]:
    """Lotes que el Agente generó y exportó para un Abogado -- usado por el
    menú "Seguimiento" (estado GENERADOS). Se filtra por exported_agente_path
    porque un lote sólo existe una vez exportado (crear y exportar son un
    mismo paso en `_on_export` de MandamientosGenerarView)."""
    conn = get_connection()
    return conn.execute(
        """
        SELECT b.*, u.full_name AS abogado_nombre
        FROM mandamiento_batches b
        LEFT JOIN users u ON u.id = b.abogado_id
        WHERE b.agente_id = ? AND b.exported_agente_path IS NOT NULL
        ORDER BY b.created_at DESC
        """,
        (agente_id,),
    ).fetchall()


def get_batch(batch_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    return conn.execute("SELECT * FROM mandamiento_batches WHERE id = ?", (batch_id,)).fetchone()


def list_rows(batch_id: int) -> list[MandamientoRow]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mandamiento_rows WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    return [MandamientoRow.from_row(r) for r in rows]


def update_row_capture(
    row_id: int,
    *,
    fecha_citatorio: str | None,
    recibe_citatorio: str | None,
    recibe_citatorio_nombre: str | None,
    fecha_notificacion: str | None,
    quien_recibe: str | None,
    quien_recibe_nombre: str | None,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE mandamiento_rows
        SET fecha_citatorio = ?, recibe_citatorio = ?, recibe_citatorio_nombre = ?,
            fecha_notificacion = ?, quien_recibe = ?, quien_recibe_nombre = ?,
            captured_at = datetime('now')
        WHERE id = ?
        """,
        (
            fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre,
            fecha_notificacion, quien_recibe, quien_recibe_nombre,
            row_id,
        ),
    )
    conn.commit()


def list_imported_files_for_agente(agente_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """
        SELECT f.id, f.original_filename, f.original_path, f.row_count, f.imported_at,
               bu.full_name AS abogado_nombre
        FROM mandamiento_imported_files f
        LEFT JOIN users bu ON bu.id = f.abogado_id
        WHERE f.agente_id = ?
        ORDER BY f.imported_at DESC
        """,
        (agente_id,),
    ).fetchall()


def list_imported_files_for_abogado(abogado_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """
        SELECT f.id, f.original_filename, f.original_path, f.row_count, f.imported_at,
               au.full_name AS agente_nombre
        FROM mandamiento_imported_files f
        LEFT JOIN users au ON au.id = f.agente_id
        WHERE f.abogado_id = ?
        ORDER BY f.imported_at DESC
        """,
        (abogado_id,),
    ).fetchall()


def set_batch_status(batch_id: int, status: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE mandamiento_batches SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, batch_id),
    )
    conn.commit()


def set_batch_finalizado(batch_id: int, finalizado: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE mandamiento_batches SET finalizado = ?, updated_at = datetime('now') WHERE id = ?",
        (1 if finalizado else 0, batch_id),
    )
    conn.commit()


def set_batch_export_path(
    batch_id: int, *, agente_path: str | None = None, abogado_path: str | None = None,
    agente_uuid: str | None = None, agente_hash: str | None = None,
    abogado_uuid: str | None = None, abogado_hash: str | None = None,
) -> None:
    """El UUID/hash del lado del Agente se llena tanto al exportar (en la
    máquina del Agente) como al importar (en la máquina del Abogado, leyendo
    lo que trae el .mcdiep recibido) -- por eso van separados de `*_path`,
    que sólo tiene sentido del lado que efectivamente escribió el archivo."""
    conn = get_connection()
    if agente_path is not None:
        conn.execute(
            "UPDATE mandamiento_batches SET exported_agente_path = ?, updated_at = datetime('now') WHERE id = ?",
            (agente_path, batch_id),
        )
    if abogado_path is not None:
        conn.execute(
            "UPDATE mandamiento_batches SET exported_abogado_path = ?, updated_at = datetime('now') WHERE id = ?",
            (abogado_path, batch_id),
        )
    if agente_uuid is not None or agente_hash is not None:
        conn.execute(
            "UPDATE mandamiento_batches SET "
            "agente_export_uuid = COALESCE(?, agente_export_uuid), "
            "agente_export_hash = COALESCE(?, agente_export_hash), "
            "updated_at = datetime('now') WHERE id = ?",
            (agente_uuid, agente_hash, batch_id),
        )
    if abogado_uuid is not None or abogado_hash is not None:
        conn.execute(
            "UPDATE mandamiento_batches SET "
            "abogado_export_uuid = COALESCE(?, abogado_export_uuid), "
            "abogado_export_hash = COALESCE(?, abogado_export_hash), "
            "updated_at = datetime('now') WHERE id = ?",
            (abogado_uuid, abogado_hash, batch_id),
        )
    conn.commit()
