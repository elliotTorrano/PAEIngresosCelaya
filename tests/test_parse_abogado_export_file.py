import openpyxl

from app.excel_io.requerimientos_export import HEADERS_ABOGADO
from app.excel_io.requerimientos_import import parse_abogado_export_file


def test_parse_abogado_export_file_maps_all_columns(tmp_path):
    path = tmp_path / "captura.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS_ABOGADO)
    ws.append([
        "F-001", "CP-001", "Juan Pérez", "Calle 1",
        "01/01/2026", "EN PUERTA", "",
        "02/01/2026", "NOMBRE", "MARIA LOPEZ",
    ])
    wb.save(path)

    rows = parse_abogado_export_file(path)

    assert len(rows) == 1
    row = rows[0]
    assert row["folio"] == "F-001"
    assert row["cta_predial"] == "CP-001"
    assert row["contribuyente"] == "Juan Pérez"
    assert row["domicilio"] == "Calle 1"
    assert row["fecha_citatorio"] == "01/01/2026"
    assert row["recibe_citatorio"] == "EN PUERTA"
    assert row["recibe_citatorio_nombre"] is None
    assert row["fecha_notificacion"] == "02/01/2026"
    assert row["quien_recibe"] == "NOMBRE"
    assert row["quien_recibe_nombre"] == "MARIA LOPEZ"


def test_parse_abogado_export_file_skips_empty_rows(tmp_path):
    path = tmp_path / "captura.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS_ABOGADO)
    ws.append(["F-001", "CP-001", "Juan Pérez", "Calle 1", "", "", "", "", "", ""])
    ws.append([None] * 10)
    wb.save(path)

    rows = parse_abogado_export_file(path)
    assert len(rows) == 1
