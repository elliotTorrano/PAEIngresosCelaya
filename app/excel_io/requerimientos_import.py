"""Lectura de los Excel del Formato de Requerimientos que sube el Agente del PAE.

Los archivos que llegan del origen no tienen un formato controlado por nosotros:
se omiten siempre las primeras 2 filas y la última, y se copian los datos libres
de las columnas B, C, D y F como FOLIO, CTA PREDIAL, CONTRIBUYENTE y DOMICILIO.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

COL_FOLIO = 2  # B
COL_CTA_PREDIAL = 3  # C
COL_CONTRIBUYENTE = 4  # D
COL_DOMICILIO = 6  # F


@dataclass
class ImportResult:
    filename: str
    rows: list[dict]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_requerimientos_file(path: Path) -> ImportResult:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        all_rows = list(sheet.iter_rows())
        # Se omiten las 2 primeras filas y la última fila del archivo.
        data_rows = all_rows[2:-1] if len(all_rows) > 3 else []

        rows = []
        for row in data_rows:
            if _is_row_empty(row):
                continue
            rows.append(
                {
                    "folio": _cell_text(row, COL_FOLIO),
                    "cta_predial": _cell_text(row, COL_CTA_PREDIAL),
                    "contribuyente": _cell_text(row, COL_CONTRIBUYENTE),
                    "domicilio": _cell_text(row, COL_DOMICILIO),
                }
            )
        return ImportResult(filename=path.name, rows=rows)
    finally:
        workbook.close()


def parse_agente_export_file(path: Path) -> list[dict]:
    """Lee el archivo que el propio programa exportó para el Abogado (formato propio,
    limpio: encabezados en la fila 1, datos desde la fila 2 — sin las filas irregulares
    de los Excel originales)."""
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows = []
        for row in sheet.iter_rows(min_row=2):
            if _is_row_empty(row):
                continue
            rows.append(
                {
                    "folio": _cell_text(row, 1),
                    "cta_predial": _cell_text(row, 2),
                    "contribuyente": _cell_text(row, 3),
                    "domicilio": _cell_text(row, 4),
                }
            )
        return rows
    finally:
        workbook.close()


def _is_row_empty(row) -> bool:
    return all(cell.value in (None, "") for cell in row)


def _cell_text(row, col_index_1based: int) -> str | None:
    idx = col_index_1based - 1
    if idx >= len(row):
        return None
    value = row[idx].value
    if value is None:
        return None
    return str(value).strip()
