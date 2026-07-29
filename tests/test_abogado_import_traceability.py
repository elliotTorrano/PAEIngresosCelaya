from unittest.mock import patch

import openpyxl

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
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
