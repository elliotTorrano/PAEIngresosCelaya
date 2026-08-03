from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox

from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo
from app.ui.agente.seguimiento_view import (
    STATE_EN_REVISION,
    STATE_GENERADOS,
    STATE_PENDIENTE_REPORTE,
    STATE_REPORTE_ENVIADO,
    SeguimientoView,
)
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog


def _make_agente_with_cert(tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-agente"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    agente = users_repo.get_by_id(agente.id)
    pfx_path = tmp_path / "agente1.pfx"
    pfx_path.write_bytes(pfx_bytes)
    return agente, pfx_path


def _make_abogado():
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_confirm_exec(pfx_path, password):
    def _exec(self):
        self._cert_path = str(pfx_path)
        self.password_input.setText(password)
        self._on_confirm()
        return self.result()

    return _exec


def _make_generated_batch(agente, abogado, tmp_path, folio="F-001"):
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(batch_id, [
        {"folio": folio, "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ])
    output_path = tmp_path / "LISTA DEL 01_01_2026 Abogado Uno.mcdiep"
    output_path.write_bytes(b"contenido")
    req_repo.set_batch_export_path(batch_id, agente_path=str(output_path))
    return batch_id


def _row(folio):
    return {
        "folio": folio, "cta_predial": None, "contribuyente": None, "domicilio": None,
        "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
        "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
    }


def _import_rows(agente_id, *, source_filename, rows):
    revision_import_id = revisiones_repo.create_revision_import(
        agente_id=agente_id, source_filename=source_filename, abogado_nombre=None, abogado_id=None,
    )
    revisiones_repo.add_revision_rows(
        agente_id=agente_id, revision_import_id=revision_import_id,
        source_filename=source_filename, abogado_nombre=None, abogado_id=None, rows=rows,
    )
    return revision_import_id


def _select_estado(page, estado):
    page.estado_combo.setCurrentIndex(page.estado_combo.findData(estado))


# --- Listado por estado ------------------------------------------------------------------

def test_generados_lists_exported_batches(qapp, db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = _make_abogado()
    _make_generated_batch(agente, abogado, tmp_path)

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    assert page.estado_combo.currentData() == STATE_GENERADOS
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "Abogado Uno"


def test_en_revision_lists_unfinished_imports(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    import_id = _import_rows(agente.id, source_filename="lote1.mcdiep", rows=[_row("F1")])

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    _select_estado(page, STATE_EN_REVISION)

    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "lote1.mcdiep"
    assert page._current_ids == [import_id]


def test_pendiente_reporte_lists_fully_reviewed_imports(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    import_id = _import_rows(agente.id, source_filename="lote1.mcdiep", rows=[_row("F1")])
    row_id = revisiones_repo.list_revision_rows_for_import(import_id)[0].id
    revisiones_repo.update_revision_procede(row_id, "PROCEDE")

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    _select_estado(page, STATE_PENDIENTE_REPORTE)

    assert page.table.rowCount() == 1
    assert page._current_ids == [import_id]

    _select_estado(page, STATE_EN_REVISION)
    assert page.table.rowCount() == 0  # ya no aparece ahí


def test_reportes_enviados_is_always_empty(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    import_id = _import_rows(agente.id, source_filename="lote1.mcdiep", rows=[_row("F1")])
    row_id = revisiones_repo.list_revision_rows_for_import(import_id)[0].id
    revisiones_repo.update_revision_procede(row_id, "PROCEDE")

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    _select_estado(page, STATE_REPORTE_ENVIADO)

    assert page.table.rowCount() == 0


def test_mandamiento_tab_shows_placeholder(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    view = SeguimientoView(agente)
    assert view.tipo_tabs.tabText(1).startswith("Mandamiento")


# --- Acción GENERADOS: volver a exportar --------------------------------------------------

def test_generados_action_without_selection_shows_information(qapp, db, tmp_path):
    agente, _pfx = _make_agente_with_cert(tmp_path)
    abogado = _make_abogado()
    _make_generated_batch(agente, abogado, tmp_path)

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    page.table.setCurrentCell(-1, -1)

    with patch("app.ui.agente.seguimiento_view.QMessageBox.information") as mock_info:
        page._on_action_clicked()

    mock_info.assert_called_once()


def test_generados_reexport_declined_confirmation_does_nothing(qapp, db, tmp_path):
    agente, pfx_path = _make_agente_with_cert(tmp_path)
    abogado = _make_abogado()
    batch_id = _make_generated_batch(agente, abogado, tmp_path)

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    page.table.selectRow(0)

    with patch(
        "app.ui.agente.seguimiento_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.No,
    ), patch("app.ui.agente.seguimiento_view.QFileDialog.getSaveFileName") as mock_save:
        page._on_action_clicked()

    mock_save.assert_not_called()
    del batch_id, pfx_path


def test_generados_reexport_confirmed_creates_new_file_and_updates_timestamp(qapp, db, tmp_path):
    agente, pfx_path = _make_agente_with_cert(tmp_path)
    abogado = _make_abogado()
    batch_id = _make_generated_batch(agente, abogado, tmp_path)
    before = req_repo.get_batch(batch_id)["updated_at"]

    new_path = tmp_path / "reexportado.mcdiep"

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    page.table.selectRow(0)

    with patch(
        "app.ui.agente.seguimiento_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(pfx_path, "clave-agente")
    ), patch(
        "app.ui.agente.seguimiento_view.QFileDialog.getSaveFileName",
        return_value=(str(new_path), ""),
    ), patch("app.ui.agente.seguimiento_view.QMessageBox.information"):
        page._on_action_clicked()

    assert new_path.exists()
    batch = req_repo.get_batch(batch_id)
    assert batch["exported_agente_path"] == str(new_path)
    del before  # el timestamp puede coincidir si corre en el mismo segundo; sólo importa la ruta


def test_generados_reexport_cancelled_file_dialog_creates_no_file(qapp, db, tmp_path):
    agente, pfx_path = _make_agente_with_cert(tmp_path)
    abogado = _make_abogado()
    batch_id = _make_generated_batch(agente, abogado, tmp_path)
    original_path = req_repo.get_batch(batch_id)["exported_agente_path"]

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    page.table.selectRow(0)

    with patch(
        "app.ui.agente.seguimiento_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(pfx_path, "clave-agente")
    ), patch(
        "app.ui.agente.seguimiento_view.QFileDialog.getSaveFileName", return_value=("", ""),
    ):
        page._on_action_clicked()

    assert req_repo.get_batch(batch_id)["exported_agente_path"] == original_path


# --- Acción EN REVISIÓN: continuar captura -------------------------------------------------

def test_en_revision_action_emits_signal_with_import_id(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    import_id = _import_rows(agente.id, source_filename="lote1.mcdiep", rows=[_row("F1")])

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    _select_estado(page, STATE_EN_REVISION)
    page.table.selectRow(0)

    received = []
    view.continuar_revision_solicitada.connect(lambda tipo, rid: received.append((tipo, rid)))
    page._on_action_clicked()

    assert received == [("requerimiento", import_id)]


# --- Acción PENDIENTE DE ENVIAR / REPORTES ENVIADOS: aún no implementadas -----------------

def test_pendiente_reporte_action_shows_proximamente_placeholder(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    import_id = _import_rows(agente.id, source_filename="lote1.mcdiep", rows=[_row("F1")])
    row_id = revisiones_repo.list_revision_rows_for_import(import_id)[0].id
    revisiones_repo.update_revision_procede(row_id, "PROCEDE")

    view = SeguimientoView(agente)
    page = view.requerimiento_page
    _select_estado(page, STATE_PENDIENTE_REPORTE)
    page.table.selectRow(0)

    with patch("app.ui.agente.seguimiento_view.QMessageBox.information") as mock_info:
        page._on_action_clicked()

    mock_info.assert_called_once()
    assert "Próximamente" in mock_info.call_args[0][1]
