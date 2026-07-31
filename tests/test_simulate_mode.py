from unittest.mock import patch

import openpyxl

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView
from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView


def _write_valid_file(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO"])
    ws.append(["x1", "F-001", "CP-001", "Juan Pérez", "y1", "Calle 1"])
    ws.append(["TOTAL", "", "", "", "", ""])
    wb.save(path)


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado():
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


# --- RequerimientosGenerarView(simulate=True) -------------------------------------

def test_simulated_agente_select_files_does_not_log_history(qapp, db, tmp_path):
    agente = _make_agente()
    _make_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente, simulate=True)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    assert len(view._rows) == 1  # el parseo/preview sí funciona
    conn = get_connection()
    rows = conn.execute("SELECT * FROM imported_files WHERE agente_id = ?", (agente.id,)).fetchall()
    assert rows == []  # pero no queda registrado


def test_simulated_agente_export_does_not_create_batch(qapp, db, tmp_path):
    agente = _make_agente()
    _make_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente, simulate=True)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information") as mock_info:
        view._on_export()

    mock_info.assert_called_once()
    assert "Simulación" in mock_info.call_args[0][1]
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0


# --- RequerimientosCaptureView(simulate=True) -------------------------------------

def test_simulated_abogado_cannot_start_new_batch(qapp, db):
    _make_agente()
    abogado = _make_abogado()

    view = RequerimientosCaptureView(abogado, simulate=True)
    with patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getOpenFileName"
    ) as mock_dialog, patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information") as mock_info:
        view._on_import()

    mock_dialog.assert_not_called()
    mock_info.assert_called_once()
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0


def test_simulated_abogado_capture_does_not_persist(qapp, db):
    agente = _make_agente()
    abogado = _make_abogado()

    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(batch_id, [
        {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ])

    view = RequerimientosCaptureView(abogado, simulate=True)
    view._load_batch(batch_id)
    row_id = view._rows[0].id

    view.table.cellWidget(0, 8).setCurrentIndex(1)  # columna "Quién recibe" (notificación) -- dispara _save_row

    assert view._rows[0].quien_recibe is not None  # el estado local sí se actualiza
    persisted = req_repo.list_rows(batch_id)
    assert persisted[0].quien_recibe is None  # pero nunca se guarda de verdad


def test_simulated_abogado_export_does_not_persist(qapp, db):
    agente = _make_agente()
    abogado = _make_abogado()

    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(batch_id, [
        {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}
    ])

    view = RequerimientosCaptureView(abogado, simulate=True)
    view._load_batch(batch_id)

    with patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information") as mock_info:
        view._on_export()

    mock_info.assert_called_once()
    assert "Simulación" in mock_info.call_args[0][1]
    batch = req_repo.list_batches_for_abogado(abogado.id)[0]
    assert batch["status"] != "EXPORTADO"
