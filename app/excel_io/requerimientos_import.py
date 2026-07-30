"""Lectura de los Excel del Formato de Requerimientos que sube el Agente del PAE.

Los archivos que llegan del origen no tienen un formato controlado por nosotros:
se omiten siempre las primeras 2 filas y la última, y se copian los datos libres
de las columnas B, C, D y F como FOLIO, CTA PREDIAL, CONTRIBUYENTE y DOMICILIO.

Se acepta tanto .xlsx/.xlsm (openpyxl) como .xls antiguo (xlrd) -- los archivos
de origen del padrón suelen venir en ese formato viejo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

COL_FOLIO = 2  # B
COL_CTA_PREDIAL = 3  # C
COL_CONTRIBUYENTE = 4  # D
COL_DOMICILIO = 6  # F

LEGACY_XLS_SUFFIXES = {".xls"}


@dataclass
class ImportResult:
    filename: str
    rows: list[dict]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_requerimientos_file(path: Path) -> ImportResult:
    all_rows = _read_all_row_values(path)
    # Se omiten las 2 primeras filas y la última fila del archivo.
    data_rows = all_rows[2:-1] if len(all_rows) > 3 else []

    rows = []
    for row in data_rows:
        if _is_row_empty(row):
            continue
        rows.append(
            {
                "folio": _value_text(row, COL_FOLIO),
                "cta_predial": _value_text(row, COL_CTA_PREDIAL),
                "contribuyente": _value_text(row, COL_CONTRIBUYENTE),
                "domicilio": _value_text(row, COL_DOMICILIO),
            }
        )
    return ImportResult(filename=path.name, rows=rows)


def parse_agente_export_file(path: Path) -> list[dict]:
    """Lee el archivo que el propio programa exportó para el Abogado (formato propio,
    limpio: encabezados en la fila 1, datos desde la fila 2 — sin las filas irregulares
    de los Excel originales). Siempre es .xlsx, porque lo genera el propio programa."""
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows = []
        for cell_row in sheet.iter_rows(min_row=2):
            row = [cell.value for cell in cell_row]
            if _is_row_empty(row):
                continue
            rows.append(
                {
                    "folio": _value_text(row, 1),
                    "cta_predial": _value_text(row, 2),
                    "contribuyente": _value_text(row, 3),
                    "domicilio": _value_text(row, 4),
                }
            )
        return rows
    finally:
        workbook.close()


def parse_abogado_export_file(path: Path) -> list[dict]:
    """Lee el archivo que el propio programa exportó con la captura del Abogado
    (formato propio, mismo criterio que parse_agente_export_file: encabezados
    en la fila 1, datos desde la fila 2, siempre .xlsx). Incluye las columnas
    de citatorio y de notificación."""
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows = []
        for cell_row in sheet.iter_rows(min_row=2):
            row = [cell.value for cell in cell_row]
            if _is_row_empty(row):
                continue
            rows.append(
                {
                    "folio": _value_text(row, 1),
                    "cta_predial": _value_text(row, 2),
                    "contribuyente": _value_text(row, 3),
                    "domicilio": _value_text(row, 4),
                    "fecha_citatorio": _value_text(row, 5),
                    "recibe_citatorio": _value_text(row, 6),
                    "recibe_citatorio_nombre": _value_text(row, 7),
                    "fecha_notificacion": _value_text(row, 8),
                    "quien_recibe": _value_text(row, 9),
                    "quien_recibe_nombre": _value_text(row, 10),
                }
            )
        return rows
    finally:
        workbook.close()


def _read_all_row_values(path: Path) -> list[list]:
    """Devuelve todas las filas del archivo como listas de valores planos,
    sin importar si es .xls (xlrd) o .xlsx/.xlsm (openpyxl)."""
    if path.suffix.lower() in LEGACY_XLS_SUFFIXES:
        return _read_all_row_values_xls(path)
    return _read_all_row_values_xlsx(path)


def _read_all_row_values_xlsx(path: Path) -> list[list]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        return [[cell.value for cell in row] for row in sheet.iter_rows()]
    finally:
        workbook.close()


def _read_all_row_values_xls(path: Path) -> list[list]:
    import xlrd

    workbook = xlrd.open_workbook(str(path))
    sheet = workbook.sheet_by_index(0)
    return [sheet.row_values(row_index) for row_index in range(sheet.nrows)]


def _is_row_empty(row: list) -> bool:
    return all(value in (None, "") for value in row)


def _value_text(row: list, col_index_1based: int) -> str | None:
    idx = col_index_1based - 1
    if idx >= len(row):
        return None
    value = row[idx]
    if value is None or value == "":
        return None
    return str(value).strip()
