import pytest

from app.db.repositories import reporte_requerimientos as reporte_repo


def _source_row(folio, **overrides):
    row = {"folio": folio, "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1", "adeudo": "1500.00"}
    row.update(overrides)
    return row


def _revision_row(folio, **overrides):
    row = {
        "folio": folio, "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1",
        "despacho": "Despacho Uno", "fecha_citatorio": "01/01/2026", "recibe_citatorio": "EN PUERTA",
        "fecha_notificacion": "02/01/2026", "quien_recibe": "NOMBRE", "observaciones": "Sin novedad.",
    }
    row.update(overrides)
    return row


def test_add_source_rows_creates_new_rows(db):
    result = reporte_repo.add_source_rows(
        [_source_row("F-001"), _source_row("F-002", adeudo="900.00")],
        lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )

    assert result.processed == 2
    assert result.duplicates == []

    rows = reporte_repo.list_rows()
    assert len(rows) == 2
    row1 = next(r for r in rows if r.folio == "F-001")
    assert row1.lista_numero == "LISTA-1"
    assert row1.cta_predial == "CP-001"
    assert row1.domicilio_ubicacion == "Calle 1"
    assert row1.adeudo == "1500.00"
    assert row1.fecha_impreso == "01/01/2026"
    assert row1.source_filename == "origen.xlsx"


def test_add_source_rows_detects_duplicate_and_does_not_overwrite(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001", adeudo="1500.00")],
        lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )

    result = reporte_repo.add_source_rows(
        [_source_row("F-001", adeudo="9999.00")],
        lista_numero="LISTA-2", fecha_impreso="05/01/2026", source_filename="origen_repetido.xlsx",
    )

    assert result.processed == 0
    assert result.duplicates == ["F-001"]

    row = reporte_repo.list_rows()[0]
    assert row.lista_numero == "LISTA-1"
    assert row.adeudo == "1500.00"
    assert row.source_filename == "origen.xlsx"


def test_add_revision_rows_creates_row_when_folio_missing(db):
    result = reporte_repo.add_revision_rows([_revision_row("F-001")])

    assert result.processed == 1
    assert result.duplicates == []

    row = reporte_repo.list_rows()[0]
    assert row.folio == "F-001"
    assert row.despacho == "Despacho Uno"
    assert row.fecha_citatorio == "01/01/2026"
    assert row.quien_recibe_citatorio == "EN PUERTA"
    assert row.fecha_diligencia == "02/01/2026"
    assert row.con_quien_notifico == "NOMBRE"
    assert row.observaciones_abogado == "Sin novedad."
    # Campos que sólo trae el import de origen quedan vacíos.
    assert row.lista_numero is None
    assert row.adeudo is None


def test_add_revision_rows_completes_existing_row_from_source_import(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001")], lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )

    result = reporte_repo.add_revision_rows([_revision_row("F-001")])

    assert result.processed == 1
    assert result.duplicates == []

    row = reporte_repo.list_rows()[0]
    assert row.lista_numero == "LISTA-1"  # conservado del import de origen
    assert row.despacho == "Despacho Uno"
    assert row.observaciones_abogado == "Sin novedad."


def test_add_revision_rows_detects_duplicate_and_does_not_overwrite(db):
    reporte_repo.add_revision_rows([_revision_row("F-001", observaciones="Primera revisión.")])

    result = reporte_repo.add_revision_rows(
        [_revision_row("F-001", observaciones="Segunda revisión distinta.", despacho="Otro despacho")]
    )

    assert result.processed == 0
    assert result.duplicates == ["F-001"]

    row = reporte_repo.list_rows()[0]
    assert row.observaciones_abogado == "Primera revisión."
    assert row.despacho == "Despacho Uno"


def test_update_manual_field_writes_allowed_column(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001")], lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )
    row_id = reporte_repo.list_rows()[0].id

    reporte_repo.update_manual_field(row_id, "observaciones_area", "Revisado por control interno.")
    reporte_repo.update_manual_field(row_id, "motivo_suspension", "Suspendido por convenio.")
    reporte_repo.update_manual_field(row_id, "fecha_extrajudicial", "10/01/2026")
    reporte_repo.update_manual_field(row_id, "domicilio_notificacion", "Calle Distinta 2")
    reporte_repo.update_manual_field(row_id, "fecha_recepcion", "15/01/2026")

    row = reporte_repo.list_rows()[0]
    assert row.observaciones_area == "Revisado por control interno."
    assert row.motivo_suspension == "Suspendido por convenio."
    assert row.fecha_extrajudicial == "10/01/2026"
    assert row.domicilio_notificacion == "Calle Distinta 2"
    assert row.fecha_recepcion == "15/01/2026"


def test_update_manual_field_rejects_non_manual_column(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001")], lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )
    row_id = reporte_repo.list_rows()[0].id

    with pytest.raises(ValueError):
        reporte_repo.update_manual_field(row_id, "folio", "OTRO-FOLIO")


def test_bulk_set_fecha_entrega_updates_only_matching_lista(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001"), _source_row("F-002")],
        lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )
    reporte_repo.add_source_rows(
        [_source_row("F-003")], lista_numero="LISTA-2", fecha_impreso="01/01/2026", source_filename="otro.xlsx",
    )

    updated = reporte_repo.bulk_set_fecha_entrega("LISTA-1", "20/01/2026")

    assert updated == 2
    rows_by_folio = {r.folio: r for r in reporte_repo.list_rows()}
    assert rows_by_folio["F-001"].fecha_entrega == "20/01/2026"
    assert rows_by_folio["F-002"].fecha_entrega == "20/01/2026"
    assert rows_by_folio["F-003"].fecha_entrega is None
