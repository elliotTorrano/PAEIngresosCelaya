"""Repositorio de la revisión del Agente sobre lo capturado por el Abogado,
para Mandamiento. Mismo flujo que app/db/repositories/revisiones.py (ver su
docstring), en tablas separadas -- Mandamiento no tiene columna DOMICILIO."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection

# Estado de un `mandamiento_revision_import` para el menú "Seguimiento" del Agente.
STATUS_EN_REVISION = "EN_REVISION"
STATUS_PENDIENTE_REPORTE = "PENDIENTE_REPORTE"
STATUS_REPORTE_ENVIADO = "REPORTE_ENVIADO"


@dataclass
class RevisionImportMandamiento:
    id: int
    agente_id: int
    source_filename: str
    abogado_nombre: str | None
    abogado_id: int | None
    imported_at: str
    status: str
    status_changed_at: str
    total_rows: int
    reviewed_rows: int
    imported_uuid: str | None
    imported_hash: str | None

    @property
    def is_reviewed(self) -> bool:
        return self.total_rows > 0 and self.reviewed_rows == self.total_rows

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RevisionImportMandamiento":
        return cls(
            id=row["id"],
            agente_id=row["agente_id"],
            source_filename=row["source_filename"],
            abogado_nombre=row["abogado_nombre"],
            abogado_id=row["abogado_id"],
            imported_at=row["imported_at"],
            status=row["status"],
            status_changed_at=row["status_changed_at"],
            total_rows=row["total_rows"],
            reviewed_rows=row["reviewed_rows"],
            imported_uuid=row["imported_uuid"],
            imported_hash=row["imported_hash"],
        )


@dataclass
class RevisionRowMandamiento:
    id: int
    agente_id: int
    revision_import_id: int | None
    source_filename: str
    abogado_nombre: str | None
    abogado_id: int | None
    folio: str | None
    cta_predial: str | None
    contribuyente: str | None
    fecha_citatorio: str | None
    recibe_citatorio: str | None
    recibe_citatorio_nombre: str | None
    fecha_notificacion: str | None
    quien_recibe: str | None
    quien_recibe_nombre: str | None
    procede: str | None
    imported_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RevisionRowMandamiento":
        return cls(
            id=row["id"],
            agente_id=row["agente_id"],
            revision_import_id=row["revision_import_id"],
            source_filename=row["source_filename"],
            abogado_nombre=row["abogado_nombre"],
            abogado_id=row["abogado_id"],
            folio=row["folio"],
            cta_predial=row["cta_predial"],
            contribuyente=row["contribuyente"],
            fecha_citatorio=row["fecha_citatorio"],
            recibe_citatorio=row["recibe_citatorio"],
            recibe_citatorio_nombre=row["recibe_citatorio_nombre"],
            fecha_notificacion=row["fecha_notificacion"],
            quien_recibe=row["quien_recibe"],
            quien_recibe_nombre=row["quien_recibe_nombre"],
            procede=row["procede"],
            imported_at=row["imported_at"],
        )


def create_revision_import(
    *, agente_id: int, source_filename: str, abogado_nombre: str | None, abogado_id: int | None,
    imported_uuid: str | None = None, imported_hash: str | None = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO mandamiento_revision_imports
            (agente_id, source_filename, abogado_nombre, abogado_id, imported_uuid, imported_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (agente_id, source_filename, abogado_nombre, abogado_id, imported_uuid, imported_hash),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def add_revision_rows(
    *, agente_id: int, revision_import_id: int, source_filename: str,
    abogado_nombre: str | None, abogado_id: int | None, rows: list[dict],
) -> None:
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO mandamiento_revision_rows (
            agente_id, revision_import_id, source_filename, abogado_nombre, abogado_id,
            folio, cta_predial, contribuyente,
            fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre,
            fecha_notificacion, quien_recibe, quien_recibe_nombre
        ) VALUES (
            :agente_id, :revision_import_id, :source_filename, :abogado_nombre, :abogado_id,
            :folio, :cta_predial, :contribuyente,
            :fecha_citatorio, :recibe_citatorio, :recibe_citatorio_nombre,
            :fecha_notificacion, :quien_recibe, :quien_recibe_nombre
        )
        """,
        [
            {
                **r,
                "agente_id": agente_id,
                "revision_import_id": revision_import_id,
                "source_filename": source_filename,
                "abogado_nombre": abogado_nombre,
                "abogado_id": abogado_id,
            }
            for r in rows
        ],
    )
    conn.commit()


def list_revision_imports(agente_id: int) -> list[RevisionImportMandamiento]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ri.id, ri.agente_id, ri.source_filename, ri.abogado_nombre, ri.abogado_id, ri.imported_at,
               ri.status, ri.status_changed_at, ri.imported_uuid, ri.imported_hash,
               COUNT(rr.id) AS total_rows,
               SUM(CASE WHEN rr.procede IS NOT NULL THEN 1 ELSE 0 END) AS reviewed_rows
        FROM mandamiento_revision_imports ri
        LEFT JOIN mandamiento_revision_rows rr ON rr.revision_import_id = ri.id
        WHERE ri.agente_id = ?
        GROUP BY ri.id
        ORDER BY ri.imported_at DESC, ri.id DESC
        """,
        (agente_id,),
    ).fetchall()
    return [RevisionImportMandamiento.from_row(r) for r in rows]


def get_revision_import(revision_import_id: int) -> RevisionImportMandamiento | None:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT ri.id, ri.agente_id, ri.source_filename, ri.abogado_nombre, ri.abogado_id, ri.imported_at,
               ri.status, ri.status_changed_at, ri.imported_uuid, ri.imported_hash,
               COUNT(rr.id) AS total_rows,
               SUM(CASE WHEN rr.procede IS NOT NULL THEN 1 ELSE 0 END) AS reviewed_rows
        FROM mandamiento_revision_imports ri
        LEFT JOIN mandamiento_revision_rows rr ON rr.revision_import_id = ri.id
        WHERE ri.id = ?
        GROUP BY ri.id
        """,
        (revision_import_id,),
    ).fetchone()
    return RevisionImportMandamiento.from_row(row) if row else None


def list_revision_rows_for_import(revision_import_id: int) -> list[RevisionRowMandamiento]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mandamiento_revision_rows WHERE revision_import_id = ? ORDER BY id",
        (revision_import_id,),
    ).fetchall()
    return [RevisionRowMandamiento.from_row(r) for r in rows]


def list_revision_rows(agente_id: int) -> list[RevisionRowMandamiento]:
    """Todas las filas de revisión del Agente, de cualquier archivo importado
    -- usado para el reporte consolidado ("Exportar revisión"), no para la
    tabla en pantalla (que muestra sólo el archivo abierto; ver
    `list_revision_rows_for_import`)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mandamiento_revision_rows WHERE agente_id = ? ORDER BY imported_at DESC, id",
        (agente_id,),
    ).fetchall()
    return [RevisionRowMandamiento.from_row(r) for r in rows]


def update_revision_procede(row_id: int, procede: str | None) -> None:
    conn = get_connection()
    conn.execute("UPDATE mandamiento_revision_rows SET procede = ? WHERE id = ?", (procede, row_id))
    row = conn.execute(
        "SELECT revision_import_id FROM mandamiento_revision_rows WHERE id = ?", (row_id,)
    ).fetchone()
    if row is not None and row["revision_import_id"] is not None:
        _sync_import_status(conn, row["revision_import_id"])
    conn.commit()


def _sync_import_status(conn: sqlite3.Connection, revision_import_id: int) -> None:
    """Recalcula EN_REVISION <-> PENDIENTE_REPORTE según cuántas filas del
    import ya tienen PROCEDE/NO PROCEDE. REPORTE_ENVIADO es un estado final:
    una vez enviado como reporte, editar una fila después no lo revierte solo."""
    current = conn.execute(
        "SELECT status FROM mandamiento_revision_imports WHERE id = ?", (revision_import_id,)
    ).fetchone()
    if current is None or current["status"] == STATUS_REPORTE_ENVIADO:
        return

    counts = conn.execute(
        """
        SELECT COUNT(*) AS total, SUM(CASE WHEN procede IS NOT NULL THEN 1 ELSE 0 END) AS reviewed
        FROM mandamiento_revision_rows WHERE revision_import_id = ?
        """,
        (revision_import_id,),
    ).fetchone()
    new_status = (
        STATUS_PENDIENTE_REPORTE
        if counts["total"] and counts["total"] == counts["reviewed"]
        else STATUS_EN_REVISION
    )
    if new_status != current["status"]:
        conn.execute(
            "UPDATE mandamiento_revision_imports SET status = ?, status_changed_at = datetime('now') WHERE id = ?",
            (new_status, revision_import_id),
        )
