"""Repositorio del "reporte general" de Requerimientos que concentra el
Reporteador: una fila por FOLIO (llave única en toda la instalación), llenada
en dos pasos independientes --

1. Importando la(s) lista(s) de origen (el mismo padrón que sube el Agente):
   crea la fila con FOLIO/CTA PREDIAL/CONTRIBUYENTE/DOMICILIO/ADEUDO, más el
   número de LISTA y la fecha de impresión que el Reporteador captura a mano
   al importar (ver app/ui/reporteador/assign_lista_dialog.py).
2. Importando la revisión que el Agente exporta al terminar "Revisar
   Formato" (`export_revision`, ver app/excel_io/requerimientos_export.py):
   completa DESPACHO y los campos de citatorio/notificación/observaciones.

En ambos pasos, si el folio que llega ya tenía ese dato cargado, NO se
sobrescribe -- se cuenta como duplicado y se avisa, para no perder una lista
o una revisión ya importada por accidente (confirmado con el usuario)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection

MANUAL_FIELDS = {
    "domicilio_notificacion",
    "fecha_recepcion",
    "observaciones_area",
    "fecha_extrajudicial",
    "motivo_suspension",
}

_REVISION_FIELD_MAP = {
    "despacho": "despacho",
    "fecha_citatorio": "fecha_citatorio",
    "recibe_citatorio": "quien_recibe_citatorio",
    "fecha_notificacion": "fecha_diligencia",
    "quien_recibe": "con_quien_notifico",
    "observaciones": "observaciones_abogado",
}
_REVISION_TRACKED_COLUMNS = ("fecha_citatorio", "quien_recibe_citatorio", "fecha_diligencia", "con_quien_notifico")


@dataclass
class ReporteRequerimientoRow:
    id: int
    lista_numero: str | None
    folio: str
    cta_predial: str | None
    contribuyente: str | None
    domicilio_ubicacion: str | None
    domicilio_notificacion: str | None
    adeudo: str | None
    despacho: str | None
    fecha_impreso: str | None
    fecha_entrega: str | None
    fecha_recepcion: str | None
    fecha_citatorio: str | None
    quien_recibe_citatorio: str | None
    fecha_diligencia: str | None
    con_quien_notifico: str | None
    observaciones_abogado: str | None
    observaciones_area: str | None
    fecha_extrajudicial: str | None
    motivo_suspension: str | None
    source_filename: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ReporteRequerimientoRow":
        return cls(
            id=row["id"], lista_numero=row["lista_numero"], folio=row["folio"],
            cta_predial=row["cta_predial"], contribuyente=row["contribuyente"],
            domicilio_ubicacion=row["domicilio_ubicacion"], domicilio_notificacion=row["domicilio_notificacion"],
            adeudo=row["adeudo"], despacho=row["despacho"], fecha_impreso=row["fecha_impreso"],
            fecha_entrega=row["fecha_entrega"], fecha_recepcion=row["fecha_recepcion"],
            fecha_citatorio=row["fecha_citatorio"], quien_recibe_citatorio=row["quien_recibe_citatorio"],
            fecha_diligencia=row["fecha_diligencia"], con_quien_notifico=row["con_quien_notifico"],
            observaciones_abogado=row["observaciones_abogado"], observaciones_area=row["observaciones_area"],
            fecha_extrajudicial=row["fecha_extrajudicial"], motivo_suspension=row["motivo_suspension"],
            source_filename=row["source_filename"],
        )


@dataclass
class ImportResult:
    processed: int
    duplicates: list[str]


def add_source_rows(
    rows: list[dict], *, lista_numero: str, fecha_impreso: str, source_filename: str
) -> ImportResult:
    conn = get_connection()
    processed = 0
    duplicates: list[str] = []
    for row in rows:
        folio = row.get("folio")
        if not folio:
            continue
        existing = conn.execute(
            "SELECT id FROM reporte_requerimientos_rows WHERE folio = ?", (folio,)
        ).fetchone()
        if existing is not None:
            duplicates.append(folio)
            continue
        conn.execute(
            """
            INSERT INTO reporte_requerimientos_rows (
                lista_numero, folio, cta_predial, contribuyente,
                domicilio_ubicacion, adeudo, fecha_impreso, source_filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lista_numero, folio, row.get("cta_predial"), row.get("contribuyente"),
                row.get("domicilio"), row.get("adeudo"), fecha_impreso, source_filename,
            ),
        )
        processed += 1
    conn.commit()
    return ImportResult(processed=processed, duplicates=duplicates)


def add_revision_rows(rows: list[dict]) -> ImportResult:
    conn = get_connection()
    processed = 0
    duplicates: list[str] = []
    for row in rows:
        folio = row.get("folio")
        if not folio:
            continue
        new_values = {dest: row.get(src) for src, dest in _REVISION_FIELD_MAP.items()}
        existing = conn.execute(
            "SELECT * FROM reporte_requerimientos_rows WHERE folio = ?", (folio,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO reporte_requerimientos_rows (
                    folio, cta_predial, contribuyente, domicilio_ubicacion,
                    despacho, fecha_citatorio, quien_recibe_citatorio,
                    fecha_diligencia, con_quien_notifico, observaciones_abogado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    folio, row.get("cta_predial"), row.get("contribuyente"), row.get("domicilio"),
                    new_values["despacho"], new_values["fecha_citatorio"], new_values["quien_recibe_citatorio"],
                    new_values["fecha_diligencia"], new_values["con_quien_notifico"],
                    new_values["observaciones_abogado"],
                ),
            )
            processed += 1
            continue

        if any(existing[col] for col in _REVISION_TRACKED_COLUMNS):
            duplicates.append(folio)
            continue

        conn.execute(
            """
            UPDATE reporte_requerimientos_rows
            SET despacho = ?, fecha_citatorio = ?, quien_recibe_citatorio = ?,
                fecha_diligencia = ?, con_quien_notifico = ?, observaciones_abogado = ?,
                updated_at = datetime('now')
            WHERE folio = ?
            """,
            (
                new_values["despacho"], new_values["fecha_citatorio"], new_values["quien_recibe_citatorio"],
                new_values["fecha_diligencia"], new_values["con_quien_notifico"],
                new_values["observaciones_abogado"], folio,
            ),
        )
        processed += 1
    conn.commit()
    return ImportResult(processed=processed, duplicates=duplicates)


def list_rows() -> list[ReporteRequerimientoRow]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM reporte_requerimientos_rows ORDER BY id").fetchall()
    return [ReporteRequerimientoRow.from_row(r) for r in rows]


def update_manual_field(row_id: int, field: str, value: str | None) -> None:
    """Actualiza una sola columna de las que sólo se llenan a mano en el
    reporte (ver MANUAL_FIELDS) -- nunca las que vienen de un import."""
    if field not in MANUAL_FIELDS:
        raise ValueError(f"Campo no editable manualmente: {field}")
    conn = get_connection()
    conn.execute(
        f"UPDATE reporte_requerimientos_rows SET {field} = ?, updated_at = datetime('now') WHERE id = ?",
        (value, row_id),
    )
    conn.commit()


def bulk_set_fecha_entrega(lista_numero: str, fecha_entrega: str) -> int:
    """Aplica la misma fecha de entrega a todas las filas de una LISTA --
    devuelve cuántas filas se actualizaron."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE reporte_requerimientos_rows SET fecha_entrega = ?, updated_at = datetime('now') "
        "WHERE lista_numero = ?",
        (fecha_entrega, lista_numero),
    )
    conn.commit()
    return cur.rowcount
