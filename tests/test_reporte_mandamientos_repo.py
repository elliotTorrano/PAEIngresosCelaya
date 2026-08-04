import pytest

from app.db.repositories import reporte_mandamientos as reporte_repo


def _source_row(folio, **overrides):
    row = {"folio": folio, "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "adeudo": "1500.00"}
    row.update(overrides)
    return row


def _revision_row(folio, **overrides):
    row = {
        "folio": folio, "cta_predial": "CP-001", "contribuyente": "Juan Pérez",
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
    row1 = next(r for r in reporte_repo.list_rows() if r.folio == "F-001")
    assert row1.lista_numero == "LISTA-1"
    assert row1.adeudo == "1500.00"


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
    assert reporte_repo.list_rows()[0].adeudo == "1500.00"


def test_add_revision_rows_creates_row_when_folio_missing(db):
    result = reporte_repo.add_revision_rows([_revision_row("F-001")])

    assert result.processed == 1
    row = reporte_repo.list_rows()[0]
    assert row.despacho == "Despacho Uno"
    assert row.observaciones_abogado == "Sin novedad."
    assert row.lista_numero is None


def test_add_revision_rows_detects_duplicate_and_does_not_overwrite(db):
    reporte_repo.add_revision_rows([_revision_row("F-001", observaciones="Primera revisión.")])
    result = reporte_repo.add_revision_rows([_revision_row("F-001", observaciones="Otra distinta.")])

    assert result.processed == 0
    assert result.duplicates == ["F-001"]
    assert reporte_repo.list_rows()[0].observaciones_abogado == "Primera revisión."


def test_update_manual_field_rejects_non_manual_column(db):
    reporte_repo.add_source_rows(
        [_source_row("F-001")], lista_numero="LISTA-1", fecha_impreso="01/01/2026", source_filename="origen.xlsx",
    )
    row_id = reporte_repo.list_rows()[0].id

    with pytest.raises(ValueError):
        reporte_repo.update_manual_field(row_id, "folio", "OTRO")


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
    assert rows_by_folio["F-003"].fecha_entrega is None
