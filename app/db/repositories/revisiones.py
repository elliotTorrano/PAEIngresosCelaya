"""Repositorio de la revisión del Agente sobre lo capturado por el Abogado:
el Agente importa el Excel que el Abogado exportó y marca PROCEDE/NO PROCEDE
por fila. Es un flujo aparte del lote original (requerimientos.py) porque el
Agente no tiene acceso directo a la base del Abogado -- cada máquina está
aislada -- así que esto vive sólo del lado de quien importa el archivo.

Cada archivo importado es su propio `revision_import` (un "evento" de
importación, igual que `requerimiento_batches` agrupa un lote): esto es lo
que permite mostrar en pantalla SÓLO las filas del archivo que se está
revisando en un momento dado, en vez de todo lo que se ha importado alguna
vez para ese Agente, y también saber qué archivos entregados por el Abogado
ya se revisaron por completo (PROCEDE/NO PROCEDE en cada fila) y cuáles
siguen pendientes."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection


@dataclass
class RevisionImport:
    id: int
    agente_id: int
    source_filename: str
    abogado_nombre: str | None
    abogado_id: int | None
    imported_at: str
    total_rows: int
    reviewed_rows: int

    @property
    def is_reviewed(self) -> bool:
        return self.total_rows > 0 and self.reviewed_rows == self.total_rows

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RevisionImport":
        return cls(
            id=row["id"],
            agente_id=row["agente_id"],
            source_filename=row["source_filename"],
            abogado_nombre=row["abogado_nombre"],
            abogado_id=row["abogado_id"],
            imported_at=row["imported_at"],
            total_rows=row["total_rows"],
            reviewed_rows=row["reviewed_rows"],
        )


@dataclass
class RevisionRow:
    id: int
    agente_id: int
    revision_import_id: int | None
    source_filename: str
    abogado_nombre: str | None
    abogado_id: int | None
    folio: str | None
    cta_predial: str | None
    contribuyente: str | None
    domicilio: str | None
    fecha_citatorio: str | None
    recibe_citatorio: str | None
    recibe_citatorio_nombre: str | None
    fecha_notificacion: str | None
    quien_recibe: str | None
    quien_recibe_nombre: str | None
    procede: str | None
    imported_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RevisionRow":
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
            domicilio=row["domicilio"],
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
    *, agente_id: int, source_filename: str, abogado_nombre: str | None, abogado_id: int | None
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO revision_imports (agente_id, source_filename, abogado_nombre, abogado_id)
        VALUES (?, ?, ?, ?)
        """,
        (agente_id, source_filename, abogado_nombre, abogado_id),
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
        INSERT INTO revision_rows (
            agente_id, revision_import_id, source_filename, abogado_nombre, abogado_id,
            folio, cta_predial, contribuyente, domicilio,
            fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre,
            fecha_notificacion, quien_recibe, quien_recibe_nombre
        ) VALUES (
            :agente_id, :revision_import_id, :source_filename, :abogado_nombre, :abogado_id,
            :folio, :cta_predial, :contribuyente, :domicilio,
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


def list_revision_imports(agente_id: int) -> list[RevisionImport]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ri.id, ri.agente_id, ri.source_filename, ri.abogado_nombre, ri.abogado_id, ri.imported_at,
               COUNT(rr.id) AS total_rows,
               SUM(CASE WHEN rr.procede IS NOT NULL THEN 1 ELSE 0 END) AS reviewed_rows
        FROM revision_imports ri
        LEFT JOIN revision_rows rr ON rr.revision_import_id = ri.id
        WHERE ri.agente_id = ?
        GROUP BY ri.id
        ORDER BY ri.imported_at DESC, ri.id DESC
        """,
        (agente_id,),
    ).fetchall()
    return [RevisionImport.from_row(r) for r in rows]


def list_revision_rows_for_import(revision_import_id: int) -> list[RevisionRow]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM revision_rows WHERE revision_import_id = ? ORDER BY id",
        (revision_import_id,),
    ).fetchall()
    return [RevisionRow.from_row(r) for r in rows]


def list_revision_rows(agente_id: int) -> list[RevisionRow]:
    """Todas las filas de revisión del Agente, de cualquier archivo importado
    -- usado para el reporte consolidado ("Exportar revisión"), no para la
    tabla en pantalla (que muestra sólo el archivo abierto; ver
    `list_revision_rows_for_import`)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM revision_rows WHERE agente_id = ? ORDER BY imported_at DESC, id",
        (agente_id,),
    ).fetchall()
    return [RevisionRow.from_row(r) for r in rows]


def update_revision_procede(row_id: int, procede: str | None) -> None:
    conn = get_connection()
    conn.execute("UPDATE revision_rows SET procede = ? WHERE id = ?", (procede, row_id))
    conn.commit()
