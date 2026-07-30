from datetime import datetime
from unittest.mock import patch

import openpyxl

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView


def _write_export_file(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"])
    ws.append(["F-001", "CP-001", "Juan Pérez", "Calle 1"])
    wb.save(path)


def test_abogado_import_logs_imported_file(qapp, db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    export_path = tmp_path / "requerimientos_abogado1_lote1.xlsx"
    _write_export_file(export_path)

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
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.information"
    ):
        view._on_export()

    mock_email.assert_not_called()
    fecha = datetime.now().strftime("%d_%m_%Y")
    expected = exports_dir() / f"requerimientos_capturado_lote{batch_id} ENTREGA {fecha}.xlsx"
    assert expected.exists()


def test_export_and_email_sends_to_agente(qapp, db):
    agente, abogado, batch_id = _make_agente_abogado_with_batch()
    view = RequerimientosCaptureView(abogado)
    view._load_batch(batch_id)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="email",
    ), patch("app.ui.abogado.requerimientos_capture_view.open_email_client") as mock_email, patch(
        "app.ui.abogado.requerimientos_capture_view.QMessageBox.information"
    ):
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
