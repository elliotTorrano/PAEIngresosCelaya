from app.db.repositories.requerimientos import RequerimientoRow
from app.excel_io.requerimientos_export import export_captured
from app.excel_io.requerimientos_import import parse_abogado_export_file


def _make_row(**overrides) -> RequerimientoRow:
    base = dict(
        id=1, batch_id=1, folio="F-001", cta_predial="CP-001", contribuyente="Juan Pérez", domicilio="Calle 1",
        fecha_citatorio="01/01/2026", recibe_citatorio="EN PUERTA", recibe_citatorio_nombre=None,
        fecha_notificacion="02/01/2026", quien_recibe="NOMBRE", quien_recibe_nombre="MARIA LOPEZ",
    )
    base.update(overrides)
    return RequerimientoRow(**base)


def test_parse_abogado_export_file_maps_all_columns(tmp_path):
    path = tmp_path / "captura.mcdiep"
    export_captured([_make_row()], path)

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


def test_parse_abogado_export_file_multiple_rows(tmp_path):
    path = tmp_path / "captura.mcdiep"
    export_captured([_make_row(id=1, folio="F-001"), _make_row(id=2, folio="F-002")], path)

    rows = parse_abogado_export_file(path)
    assert len(rows) == 2
    assert rows[1]["folio"] == "F-002"
