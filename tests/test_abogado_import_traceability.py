from datetime import datetime
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox

from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.requerimientos_export import export_for_abogado
from app.excel_io.requerimientos_import import parse_abogado_export_file
from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView


def _make_agente_with_cert():
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-segura"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    private_key, _certificate = load_bundle(pfx_bytes, "clave-segura")
    return users_repo.get_by_id(agente.id), private_key


def test_abogado_import_logs_imported_file(qapp, db, tmp_path):
    agente, private_key = _make_agente_with_cert()
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    export_path = tmp_path / "requerimientos_abogado1_lote1.mcdiep"
    export_for_abogado(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}],
        export_path, agente=agente, abogado=abogado, private_key=private_key,
    )

    view = RequerimientosCaptureView(abogado)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getOpenFileName",
        return_value=(str(export_path), ""),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_import()

    conn = get_connection()
    rows = conn.execute("SELECT * FROM imported_files WHERE abogado_id = ?", (abogado.id,)).fetchall()

    assert len(rows) == 1
    assert rows[0]["agente_id"] == agente.id
    assert rows[0]["original_filename"] == export_path.name
    assert rows[0]["row_count"] == 1
    assert rows[0]["imported_at"] is not None


def test_abogado_import_rejects_file_signed_for_another_abogado(qapp, db, tmp_path):
    agente, private_key = _make_agente_with_cert()
    other_abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    this_abogado = users_repo.create_user(
        username="abogado2", role=ROLE_ABOGADO, full_name="Abogado Dos", email="c@c.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    export_path = tmp_path / "para_otro.mcdiep"
    export_for_abogado(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}],
        export_path, agente=agente, abogado=other_abogado, private_key=private_key,
    )

    view = RequerimientosCaptureView(this_abogado)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getOpenFileName",
        return_value=(str(export_path), ""),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.critical") as mock_critical:
        view._on_import()

    mock_critical.assert_called_once()
    conn = get_connection()
    rows = conn.execute("SELECT * FROM imported_files WHERE abogado_id = ?", (this_abogado.id,)).fetchall()
    assert rows == []


def _make_agente_abogado_with_batch():
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(batch_id, [
        {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ])
    # La fila queda capturada (no vacía) para que el filtro de exportación
    # ("sólo filas modificadas") no la excluya en las pruebas de export.
    row_id = req_repo.list_rows(batch_id)[0].id
    req_repo.update_row_capture(
        row_id,
        fecha_citatorio="01/01/2024", recibe_citatorio="EN PUERTA", recibe_citatorio_nombre=None,
        fecha_notificacion="01/01/2024", quien_recibe="EN PUERTA", quien_recibe_nombre=None,
    )
    return agente, abogado, batch_id


def test_export_only_does_not_call_email(qapp, db):
    from app.utils.paths import exports_dir

    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch("app.ui.abogado.requerimientos_capture_view.open_email_client") as mock_email, patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_export()

    mock_email.assert_not_called()
    fecha = datetime.now().strftime("%d_%m_%Y")
    expected = exports_dir() / f"requerimientos_capturado_lote{batch_id} ENTREGA {fecha}.mcdiep"
    assert expected.exists()


def test_export_and_email_sends_to_agente(qapp, db):
    from app.utils.paths import exports_dir

    agente, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="email",
    ), patch("app.ui.abogado.requerimientos_capture_view.open_email_client") as mock_email, patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_export()

    mock_email.assert_called_once()
    assert mock_email.call_args.kwargs["to_email"] == agente.email


def test_export_cancel_does_not_write_or_change_status(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="cancel",
    ), patch("app.ui.abogado.requerimientos_capture_view.export_captured") as mock_export:
        view._on_export()

    mock_export.assert_not_called()
    batch = req_repo.get_batch(batch_id)
    assert batch["status"] != "EXPORTADO"


def test_export_cancelled_folder_picker_does_not_write_or_change_status(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory", return_value=""
    ), patch("app.ui.abogado.requerimientos_capture_view.export_captured") as mock_export:
        view._on_export()

    mock_export.assert_not_called()
    batch = req_repo.get_batch(batch_id)
    assert batch["status"] != "EXPORTADO"


# --- Finalizar / editar --------------------------------------------------------------

def test_finalize_persists_and_locks_widgets(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        view._on_finalize()

    assert req_repo.get_batch(batch_id)["finalizado"] == 1
    assert view._current_batch_finalizado is True
    assert view.finalize_btn.isHidden() is True
    assert view.edit_btn.isHidden() is False
    assert view.table.cellWidget(0, 4).isEnabled() is False  # fecha citatorio
    assert view.table.cellWidget(0, 5).isEnabled() is False  # recibe citatorio


def test_finalize_declined_confirmation_does_nothing(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.No,
    ):
        view._on_finalize()

    assert req_repo.get_batch(batch_id)["finalizado"] == 0
    assert view._current_batch_finalizado is False


def test_save_row_no_ops_while_finalized(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)
    row_id = view._rows[0].id
    before = req_repo.list_rows(batch_id)[0].recibe_citatorio_nombre

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        view._on_finalize()

    view._rows[0].recibe_citatorio_nombre = "INTENTO DE CAMBIO"  # simula edición local directa
    view._save_row(row_id)

    persisted = req_repo.list_rows(batch_id)[0]
    assert persisted.recibe_citatorio_nombre == before


def test_unlock_edit_re_enables_widgets(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        view._on_finalize()

    view._on_unlock_edit()

    assert req_repo.get_batch(batch_id)["finalizado"] == 0
    assert view._current_batch_finalizado is False
    assert view.finalize_btn.isHidden() is False
    assert view.edit_btn.isHidden() is True
    assert view.table.cellWidget(0, 4).isEnabled() is True


def test_finalize_blocked_in_simulation(qapp, db):
    _, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado, simulate=True)
    view._load_batch(batch_id)

    with patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information") as mock_info:
        view._on_finalize()

    mock_info.assert_called_once()
    assert req_repo.get_batch(batch_id)["finalizado"] == 0


# --- Exportación: sólo filas modificadas ----------------------------------------------

def test_export_excludes_untouched_rows(qapp, db, tmp_path):
    from app.utils.paths import exports_dir

    agente, abogado, batch_id = _make_agente_abogado_with_batch()
    # Segunda fila que se queda tal cual se importó (sin captura).
    req_repo.add_rows(batch_id, [
        {"folio": "F-002", "cta_predial": "CP-002", "contribuyente": "María López", "domicilio": "Calle 2"}
    ])

    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)
    assert len(view._rows) == 2

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_export()

    fecha = datetime.now().strftime("%d_%m_%Y")
    output_path = exports_dir() / f"requerimientos_capturado_lote{batch_id} ENTREGA {fecha}.mcdiep"
    exported_rows = parse_abogado_export_file(output_path)
    assert len(exported_rows) == 1
    assert exported_rows[0]["folio"] == "F-001"


def test_export_warns_when_nothing_modified(qapp, db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(batch_id, [
        {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ])

    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.warning") as mock_warn, patch(
        "app.ui.abogado.requerimientos_capture_view.export_captured"
    ) as mock_export:
        view._on_export()

    mock_warn.assert_called_once()
    mock_export.assert_not_called()


def test_export_overwrite_confirmation_declined_keeps_existing_file(qapp, db):
    from app.utils.paths import exports_dir

    _, abogado, batch_id = _make_agente_abogado_with_batch()

    fecha = datetime.now().strftime("%d_%m_%Y")
    existing = exports_dir() / f"requerimientos_capturado_lote{batch_id} ENTREGA {fecha}.mcdiep"
    existing.write_bytes(b"contenido previo")

    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.No,
    ):
        view._on_export()

    assert existing.read_bytes() == b"contenido previo"
    batch = req_repo.get_batch(batch_id)
    assert batch["status"] != "EXPORTADO"
