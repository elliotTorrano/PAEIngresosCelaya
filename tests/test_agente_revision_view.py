from unittest.mock import patch

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo
from app.db.repositories.requerimientos import RequerimientoRow
from app.excel_io.requerimientos_export import HEADERS_ABOGADO, export_captured
from app.ui.agente.requerimientos_import_view import RequerimientosImportView


def _make_agente_abogado():
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    return agente


def _write_captura_file(path):
    row = RequerimientoRow(
        id=1, batch_id=1, folio="F-001", cta_predial="CP-001", contribuyente="Juan Pérez", domicilio="Calle 1",
        fecha_citatorio="01/01/2026", recibe_citatorio="EN PUERTA", recibe_citatorio_nombre=None,
        fecha_notificacion="02/01/2026", quien_recibe="EN PUERTA", quien_recibe_nombre=None,
    )
    export_captured([row], path)


def test_import_revision_persists_rows_and_refreshes_table(qapp, db, tmp_path):
    agente = _make_agente_abogado()
    path = tmp_path / "captura.mcdiep"
    _write_captura_file(path)

    view = RequerimientosImportView(agente)
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileName",
        return_value=(str(path), ""),
    ), patch("app.ui.agente.requerimientos_import_view.QMessageBox.information"):
        view._on_import_revision()

    rows = revisiones_repo.list_revision_rows(agente.id)
    assert len(rows) == 1
    assert rows[0].folio == "F-001"
    assert view.revision_table.rowCount() == 1


def test_import_revision_stores_and_displays_abogado_id(qapp, db, tmp_path):
    agente = _make_agente_abogado()
    abogado = users_repo.list_by_role(ROLE_ABOGADO)[0]
    path = tmp_path / "captura.mcdiep"
    _write_captura_file(path)

    view = RequerimientosImportView(agente)
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileName",
        return_value=(str(path), ""),
    ), patch("app.ui.agente.requerimientos_import_view.QMessageBox.information"):
        view._on_import_revision()

    rows = revisiones_repo.list_revision_rows(agente.id)
    assert rows[0].abogado_id == abogado.id

    id_col = len(HEADERS_ABOGADO) + 1  # a la derecha de la columna Procede
    assert view.revision_table.item(0, id_col).text() == str(abogado.id)


def test_procede_combo_change_persists(qapp, db):
    agente = _make_agente_abogado()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None, abogado_id=None,
        rows=[{
            "folio": "F-001", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )
    view = RequerimientosImportView(agente)
    row_id = revisiones_repo.list_revision_rows(agente.id)[0].id
    combo = view.revision_table.cellWidget(0, len(HEADERS_ABOGADO))  # columna PROCEDE

    combo.setCurrentIndex(combo.findData("PROCEDE"))

    refreshed = revisiones_repo.list_revision_rows(agente.id)[0]
    assert refreshed.id == row_id
    assert refreshed.procede == "PROCEDE"


def test_export_revision_writes_file(qapp, db, tmp_path):
    from app.utils.paths import exports_dir

    agente = _make_agente_abogado()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None, abogado_id=None,
        rows=[{
            "folio": "F-001", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )
    view = RequerimientosImportView(agente)

    with patch("app.ui.agente.requerimientos_import_view.QMessageBox.information"):
        view._on_export_revision()

    matches = list(exports_dir().glob("REVISION DEL *.xlsx"))
    assert len(matches) == 1


def test_simulate_mode_blocks_import_procede_and_export(qapp, db, tmp_path):
    agente = _make_agente_abogado()
    path = tmp_path / "captura.mcdiep"
    _write_captura_file(path)

    view = RequerimientosImportView(agente, simulate=True)

    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileName"
    ) as mock_dialog, patch("app.ui.agente.requerimientos_import_view.QMessageBox.information") as mock_info:
        view._on_import_revision()
    mock_dialog.assert_not_called()
    mock_info.assert_called_once()
    assert revisiones_repo.list_revision_rows(agente.id) == []

    # Fila real preexistente (de otra sesión no-simulada) para probar que el
    # cambio de PROCEDE en modo simulación no persiste.
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None, abogado_id=None,
        rows=[{
            "folio": "F-001", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )
    view._refresh_revision_table()
    combo = view.revision_table.cellWidget(0, len(HEADERS_ABOGADO))
    combo.setCurrentIndex(combo.findData("PROCEDE"))
    assert revisiones_repo.list_revision_rows(agente.id)[0].procede is None

    with patch("app.ui.agente.requerimientos_import_view.QMessageBox.information") as mock_info2:
        view._on_export_revision()
    mock_info2.assert_called_once()
    assert "Simulación" in mock_info2.call_args[0][1]


# --- Buscar fila por FOLIO/CTA PREDIAL/CONTRIBUYENTE -----------------------------------

def _rows_for_search():
    return [
        {
            "folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1",
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        },
        {
            "folio": "F-002", "cta_predial": "CP-002", "contribuyente": "María López", "domicilio": "Calle 2",
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        },
    ]


def test_search_revision_by_contribuyente_selects_matching_row(qapp, db):
    agente = _make_agente_abogado()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None, abogado_id=None,
        rows=_rows_for_search(),
    )
    view = RequerimientosImportView(agente)

    view.revision_search_field_combo.setCurrentIndex(
        view.revision_search_field_combo.findText("CONTRIBUYENTE")
    )
    view.revision_search_input.setText("lópez")
    view._on_search_revision()

    assert view.revision_table.currentRow() == 1


def test_search_revision_no_match_shows_information(qapp, db):
    agente = _make_agente_abogado()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None, abogado_id=None,
        rows=_rows_for_search(),
    )
    view = RequerimientosImportView(agente)
    view.revision_search_input.setText("no existe en ninguna fila")

    with patch("app.ui.agente.requerimientos_import_view.QMessageBox.information") as mock_info:
        view._on_search_revision()

    mock_info.assert_called_once()
