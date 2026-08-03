"""Genera el PDF de acompañamiento del Formato de Mandamientos -- mismo motor
de armado (cabecera, sello CFDI, QR corrido, identidad UUID/hash, doble cara)
que app/pdf_io/requerimientos_pdf.py, reutilizado tal cual porque no tiene
ningún contenido específico de Requerimiento: sólo cambian aquí los
encabezados de columnas (sin DOMICILIO, que Mandamiento no trae) y el texto
institucional del formato."""

from __future__ import annotations

from pathlib import Path

from app.db.repositories.mandamientos import MandamientoRow
from app.db.repositories.users import User
from app.pdf_io.requerimientos_pdf import (  # noqa: F401 -- re-exportados para uso simétrico desde la UI
    DocumentIdentity,
    _render_pdf,
    compute_identity,
    new_document_uuid,
    suggested_filename,
)

FORMATO_TITULO = "FORMATO: ENTREGA DE MANDAMIENTOS DE EJECUCIÓN"
DOCUMENTO_TITULO = "Entrega de Mandamientos de Ejecución"

HEADERS_AGENTE = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE"]
HEADERS_ABOGADO = HEADERS_AGENTE + [
    "Fecha de citatorio", "Recibe citatorio", "Nombre",
    "Fecha de notificación", "Quién recibe", "Nombre",
]


def export_agente_pdf(
    pdf_path: Path, *, agente: User, abogado: User, rows: list[dict], filename: str, identity: DocumentIdentity,
) -> None:
    """PDF que acompaña la exportación del Agente. Ver
    app/pdf_io/requerimientos_pdf.py::export_agente_pdf."""
    table_rows = [
        [row["folio"] or "", row["cta_predial"] or "", row["contribuyente"] or ""]
        for row in rows
    ]
    _render_pdf(
        pdf_path, agente_nombre=agente.full_name, abogado_nombre=abogado.full_name, filename=filename,
        headers=HEADERS_AGENTE, table_rows=table_rows, quien_recibe_values=[None] * len(rows),
        total_mode="all", include_notificacion_counters=False, identity=identity,
        formato_titulo=FORMATO_TITULO, documento_titulo=DOCUMENTO_TITULO,
    )


def export_abogado_pdf(
    pdf_path: Path, *, agente: User, abogado: User, rows: list[MandamientoRow], filename: str,
    identity: DocumentIdentity,
) -> None:
    """PDF que acompaña la exportación del Abogado. Ver
    app/pdf_io/requerimientos_pdf.py::export_abogado_pdf."""
    table_rows = [
        [
            row.folio or "", row.cta_predial or "", row.contribuyente or "",
            row.fecha_citatorio or "", row.recibe_citatorio or "", row.recibe_citatorio_nombre or "",
            row.fecha_notificacion or "", row.quien_recibe or "", row.quien_recibe_nombre or "",
        ]
        for row in rows
    ]
    _render_pdf(
        pdf_path, agente_nombre=agente.full_name, abogado_nombre=abogado.full_name, filename=filename,
        headers=HEADERS_ABOGADO, table_rows=table_rows, quien_recibe_values=[row.quien_recibe for row in rows],
        total_mode="filled", include_notificacion_counters=True, identity=identity,
        formato_titulo=FORMATO_TITULO, documento_titulo=DOCUMENTO_TITULO,
    )
