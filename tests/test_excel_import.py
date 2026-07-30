from pathlib import Path

import openpyxl

from app.excel_io.requerimientos_import import parse_agente_export_file, parse_requerimientos_file


def _write_raw_excel(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["irrelevant title row"])  # fila 1 (se omite)
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO"])  # fila 2 (se omite)
    ws.append(["x1", "F-001", "CP-001", "Juan Pérez", "y1", "Calle 1"])
    ws.append(["x2", "F-002", "CP-002", "María López", "y2", "Calle 2"])
    ws.append(["TOTAL", "", "", "", "", ""])  # última fila (se omite)
    wb.save(path)


def test_parse_requerimientos_file_skips_rows_and_maps_columns(tmp_path):
    path = tmp_path / "origen.xlsx"
    _write_raw_excel(path)

    result = parse_requerimientos_file(path)

    assert result.row_count == 2
    assert result.rows[0] == {
        "folio": "F-001",
        "cta_predial": "CP-001",
        "contribuyente": "Juan Pérez",
        "domicilio": "Calle 1",
    }
    assert result.rows[1]["folio"] == "F-002"


def test_parse_requerimientos_file_supports_legacy_xls(tmp_path):
    import xlwt

    path = tmp_path / "origen.xls"
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Hoja1")
    rows = [
        ["irrelevant title row"],
        ["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO"],
        ["x1", "F-001", "CP-001", "Juan Pérez", "y1", "Calle 1"],
        ["x2", "F-002", "CP-002", "María López", "y2", "Calle 2"],
        ["TOTAL", "", "", "", "", ""],
    ]
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            ws.write(r, c, value)
    wb.save(str(path))

    result = parse_requerimientos_file(path)

    assert result.row_count == 2
    assert result.rows[0] == {
        "folio": "F-001",
        "cta_predial": "CP-001",
        "contribuyente": "Juan Pérez",
        "domicilio": "Calle 1",
    }
    assert result.rows[1]["folio"] == "F-002"


def test_parse_agente_export_file_reads_clean_headers(tmp_path):
    path = tmp_path / "exportado.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"])
    ws.append(["F-001", "CP-001", "Juan Pérez", "Calle 1"])
    wb.save(path)

    rows = parse_agente_export_file(path)

    assert rows == [
        {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ]
