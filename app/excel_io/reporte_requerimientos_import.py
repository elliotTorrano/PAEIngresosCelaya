"""Parsers de lo que el Reporteador importa a su reporte general de
Requerimientos:

1. `parse_source_file`: la(s) lista(s) de origen -- el mismo padrón .xls/.xlsx
   que sube el Agente, pero leyendo ADEMÁS la columna ADEUDO (K), que el
   parser del Agente (app/excel_io/requerimientos_import.py) nunca ha
   necesitado leer.
2. `parse_revision_file`: el .xlsx que el Agente exporta al terminar
   "Revisar Formato" (`export_revision`, ver
   app/excel_io/requerimientos_export.py) -- Excel normal, no .mcdiep.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

from app.excel_io.requerimientos_import import (
    _folio_text,
    _is_row_empty,
    _read_all_row_values,
    _value_text,
)

COL_FOLIO = 2  # B
COL_CTA_PREDIAL = 3  # C
COL_CONTRIBUYENTE = 4  # D
COL_DOMICILIO = 6  # F
COL_ADEUDO = 11  # K

# Mapeo encabezado -> clave del dict de fila, para leer el archivo de
# revisión por nombre de columna (no por posición fija).
_REVISION_HEADER_MAP = {
    "FOLIO": "folio",
    "CTA PREDIAL": "cta_predial",
    "CONTRIBUYENTE": "contribuyente",
    "DOMICILIO": "domicilio",
    "Fecha de citatorio": "fecha_citatorio",
    "Recibe citatorio": "recibe_citatorio",
    "Fecha de Notificación de citatorio": "fecha_notificacion",
    "Quién recibe el citatorio": "quien_recibe",
    "Observaciones": "observaciones",
    "Despacho": "despacho",
}


@dataclass
class ImportResult:
    filename: str
    rows: list[dict]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_source_file(path: Path) -> ImportResult:
    all_rows = _read_all_row_values(path)
    # Mismo criterio que el parser del Agente: se omiten las 2 primeras
    # filas y la última fila del archivo.
    data_rows = all_rows[2:-1] if len(all_rows) > 3 else []

    rows = []
    for row in data_rows:
        if _is_row_empty(row):
            continue
        rows.append(
            {
                "folio": _folio_text(row, COL_FOLIO),
                "cta_predial": _value_text(row, COL_CTA_PREDIAL),
                "contribuyente": _value_text(row, COL_CONTRIBUYENTE),
                "domicilio": _value_text(row, COL_DOMICILIO),
                "adeudo": _value_text(row, COL_ADEUDO),
            }
        )
    return ImportResult(filename=path.name, rows=rows)


def parse_revision_file(path: Path) -> ImportResult:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            return ImportResult(filename=path.name, rows=[])
        header_index = {str(name).strip(): idx for idx, name in enumerate(header) if name is not None}

        rows = []
        for values in rows_iter:
            if values is None or all(v in (None, "") for v in values):
                continue
            row = {}
            for header_name, key in _REVISION_HEADER_MAP.items():
                idx = header_index.get(header_name)
                value = values[idx] if idx is not None and idx < len(values) else None
                row[key] = str(value).strip() if value not in (None, "") else None
            rows.append(row)
        return ImportResult(filename=path.name, rows=rows)
    finally:
        workbook.close()
