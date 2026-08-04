import openpyxl

from app.db.repositories.revisiones import RevisionRow
from app.db.repositories.revisiones_mandamiento import RevisionRowMandamiento
from app.excel_io import reporte_mandamientos_import, reporte_requerimientos_import
from app.excel_io.mandamientos_export import export_revision as export_revision_mandamiento
from app.excel_io.requerimientos_export import export_revision as export_revision_requerimientos


def _write_requerimientos_source_file(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO", "G", "H", "I", "J", "ADEUDO"])
    ws.append(["x1", "F-001", "CP-001", "Juan Pérez", "y1", "Calle 1", "", "", "", "", "1500.00"])
    ws.append(["TOTAL", "", "", "", "", "", "", "", "", "", ""])
    wb.save(path)


def _write_mandamientos_source_file(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "F", "G", "H", "ADEUDO"])
    ws.append(["x1", "F-001", "CP-001", "Juan Pérez", "", "", "", "", "900.00"])
    ws.append(["TOTAL", "", "", "", "", "", "", "", ""])
    wb.save(path)


def test_parse_requerimientos_source_file_reads_adeudo_from_column_k(tmp_path):
    path = tmp_path / "origen.xlsx"
    _write_requerimientos_source_file(path)

    result = reporte_requerimientos_import.parse_source_file(path)

    assert result.row_count == 1
    row = result.rows[0]
    assert row["folio"] == "F-001"
    assert row["cta_predial"] == "CP-001"
    assert row["contribuyente"] == "Juan Pérez"
    assert row["domicilio"] == "Calle 1"
    assert row["adeudo"] == "1500.00"


def test_parse_mandamientos_source_file_reads_adeudo_from_column_i(tmp_path):
    path = tmp_path / "origen.xlsx"
    _write_mandamientos_source_file(path)

    result = reporte_mandamientos_import.parse_source_file(path)

    assert result.row_count == 1
    row = result.rows[0]
    assert row["folio"] == "F-001"
    assert row["cta_predial"] == "CP-001"
    assert row["contribuyente"] == "Juan Pérez"
    assert row["adeudo"] == "900.00"


def test_parse_requerimientos_revision_file_maps_despacho_and_observaciones(tmp_path):
    row = RevisionRow(
        id=1, agente_id=1, revision_import_id=1, source_filename="x.xlsx",
        abogado_nombre="Despacho Uno", abogado_id=None,
        folio="F-001", cta_predial="CP-001", contribuyente="Juan Pérez", domicilio="Calle 1",
        fecha_citatorio="01/01/2026", recibe_citatorio="EN PUERTA", recibe_citatorio_nombre=None,
        fecha_notificacion="02/01/2026", quien_recibe="NOMBRE", quien_recibe_nombre="MARIA LOPEZ",
        observaciones="No se encontró a nadie.", procede="PROCEDE", imported_at="2026-01-01 10:00:00",
    )
    path = tmp_path / "revision.xlsx"
    export_revision_requerimientos([row], path)

    result = reporte_requerimientos_import.parse_revision_file(path)

    assert result.row_count == 1
    parsed = result.rows[0]
    assert parsed["folio"] == "F-001"
    assert parsed["cta_predial"] == "CP-001"
    assert parsed["contribuyente"] == "Juan Pérez"
    assert parsed["domicilio"] == "Calle 1"
    assert parsed["fecha_citatorio"] == "01/01/2026"
    assert parsed["recibe_citatorio"] == "EN PUERTA"
    assert parsed["fecha_notificacion"] == "02/01/2026"
    assert parsed["quien_recibe"] == "NOMBRE"
    assert parsed["observaciones"] == "No se encontró a nadie."
    assert parsed["despacho"] == "Despacho Uno"


def test_parse_mandamientos_revision_file_maps_despacho_and_observaciones(tmp_path):
    row = RevisionRowMandamiento(
        id=1, agente_id=1, revision_import_id=1, source_filename="x.xlsx",
        abogado_nombre="Despacho Dos", abogado_id=None,
        folio="F-002", cta_predial="CP-002", contribuyente="María López",
        fecha_citatorio="03/01/2026", recibe_citatorio="NOMBRE", recibe_citatorio_nombre="PEDRO",
        fecha_notificacion="04/01/2026", quien_recibe="EN PUERTA", quien_recibe_nombre=None,
        observaciones="Domicilio cerrado.", procede="NO PROCEDE", imported_at="2026-01-01 10:00:00",
    )
    path = tmp_path / "revision.xlsx"
    export_revision_mandamiento([row], path)

    result = reporte_mandamientos_import.parse_revision_file(path)

    assert result.row_count == 1
    parsed = result.rows[0]
    assert parsed["folio"] == "F-002"
    assert parsed["observaciones"] == "Domicilio cerrado."
    assert parsed["despacho"] == "Despacho Dos"
