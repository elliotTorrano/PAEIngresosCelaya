"""Exportación a Excel del Formato de Requerimientos (Agente -> Abogado y captura final)."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.db.repositories.requerimientos import RequerimientoRow

HEADERS_AGENTE = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"]
HEADERS_ABOGADO = HEADERS_AGENTE + [
    "Fecha de Notificación de citatorio",
    "Quién recibe el citatorio",
    "Nombre de quien recibe",
]


def export_for_abogado(rows: list[dict], output_path: Path) -> None:
    """Exporta lo importado por el Agente del PAE, listo para entregarle al Abogado."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Requerimientos"
    sheet.append(HEADERS_AGENTE)
    for row in rows:
        sheet.append([row["folio"], row["cta_predial"], row["contribuyente"], row["domicilio"]])
    workbook.save(output_path)


def export_captured(rows: list[RequerimientoRow], output_path: Path) -> None:
    """Exporta el resultado final capturado por el Abogado."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Requerimientos"
    sheet.append(HEADERS_ABOGADO)
    for row in rows:
        sheet.append(
            [
                row.folio,
                row.cta_predial,
                row.contribuyente,
                row.domicilio,
                row.fecha_notificacion,
                row.quien_recibe,
                row.quien_recibe_nombre,
            ]
        )
    workbook.save(output_path)
