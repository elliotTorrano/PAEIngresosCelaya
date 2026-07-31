"""Repositorio de la revisión del Agente sobre lo capturado por el Abogado:
el Agente importa el Excel que el Abogado exportó y marca PROCEDE/NO PROCEDE
por fila. Es un flujo aparte del lote original (requerimientos.py) porque el
Agente no tiene acceso directo a la base del Abogado -- cada máquina está
aislada -- así que esto vive sólo del lado de quien importa el archivo."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection


@dataclass
class RevisionRow:
    id: int
    agente_id: int
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


def add_revision_rows(
    *, agente_id: int, source_filename: str, abogado_nombre: str | None, abogado_id: int | None,
    rows: list[dict],
) -> None:
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO revision_rows (
            agente_id, source_filename, abogado_nombre, abogado_id,
            folio, cta_predial, contribuyente, domicilio,
            fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre,
            fecha_notificacion, quien_recibe, quien_recibe_nombre
        ) VALUES (
            :agente_id, :source_filename, :abogado_nombre, :abogado_id,
            :folio, :cta_predial, :contribuyente, :domicilio,
            :fecha_citatorio, :recibe_citatorio, :recibe_citatorio_nombre,
            :fecha_notificacion, :quien_recibe, :quien_recibe_nombre
        )
        """,
        [
            {
                **r,
                "agente_id": agente_id,
                "source_filename": source_filename,
                "abogado_nombre": abogado_nombre,
                "abogado_id": abogado_id,
            }
            for r in rows
        ],
    )
    conn.commit()


def list_revision_rows(agente_id: int) -> list[RevisionRow]:
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
