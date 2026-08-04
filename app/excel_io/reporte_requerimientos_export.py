"""Exportación del reporte general de Requerimientos que concentra el
Reporteador -- las 19 columnas pedidas, en orden. Se usa tanto para el
archivo maestro (regenerado completo tras cada cambio) como para la
exportación manual a cualquier ubicación."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.db.repositories.reporte_requerimientos import ReporteRequerimientoRow

HEADERS = [
    "LISTA",
    "FOLIO",
    "CUENTA PREDIAL",
    "CONTRIBUYENTE",
    "DOMICILIO DE UBICACIÓN",
    "DOMICILIO DE NOTIFICACIÓN",
    "ADEUDO",
    "DESPACHO",
    "FECHA IMPRESO",
    "FECHA DE ENTREGA",
    "FECHA DE RECEPCIÓN",
    "FECHA DE CITATORIO",
    "QUIEN RECIBE CITATORIO",
    "FECHA DE DILIGENCIA",
    "CON QUIEN SE NOTIFICÓ",
    "OBSERVACIONES ABOGADO",
    "OBSERVACIONES DEL ÁREA",
    "FECHA EXTRAJUDICIAL",
    "MOTIVO SUSPENSIÓN PAE",
]


def export_reporte_xlsx(rows: list[ReporteRequerimientoRow], output_path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Reporte General"
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(
            [
                row.lista_numero,
                row.folio,
                row.cta_predial,
                row.contribuyente,
                row.domicilio_ubicacion,
                row.domicilio_notificacion,
                row.adeudo,
                row.despacho,
                row.fecha_impreso,
                row.fecha_entrega,
                row.fecha_recepcion,
                row.fecha_citatorio,
                row.quien_recibe_citatorio,
                row.fecha_diligencia,
                row.con_quien_notifico,
                row.observaciones_abogado,
                row.observaciones_area,
                row.fecha_extrajudicial,
                row.motivo_suspension,
            ]
        )
    workbook.save(output_path)
