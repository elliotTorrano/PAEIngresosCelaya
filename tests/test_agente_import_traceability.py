from datetime import datetime
from unittest.mock import MagicMock, patch

import openpyxl
from PySide6.QtWidgets import QDialog

from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import users as users_repo
from app.ui.agente.requerimientos_import_view import RequerimientosImportView


def _write_valid_file(path, folio="F-001"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO"])
    ws.append(["x1", folio, "CP-001", "Juan Pérez", "y1", "Calle 1"])
    ws.append(["TOTAL", "", "", "", "", ""])
    wb.save(path)


def _make_agente_abogado():
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-segura"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    agente = users_repo.get_by_id(agente.id)
    private_key, _certificate = load_bundle(pfx_bytes, "clave-segura")

    users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    return agente, private_key


def _mock_confirm_dialog(private_key):
    mock = MagicMock()
    mock.exec.return_value = QDialog.DialogCode.Accepted
    mock.private_key = private_key
    return mock


def test_selecting_a_file_logs_it_immediately(qapp, db, tmp_path):
    agente, _private_key = _make_agente_abogado()
    path = tmp_path / "lote_julio.xlsx"
    _write_valid_file(path)

    view = RequerimientosImportView(agente)

    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    conn = get_connection()
    rows = conn.execute("SELECT * FROM imported_files WHERE agente_id = ?", (agente.id,)).fetchall()

    assert len(rows) == 1
    assert rows[0]["original_filename"] == "lote_julio.xlsx"
    assert rows[0]["row_count"] == 1
    assert rows[0]["imported_at"] is not None
    assert rows[0]["batch_id"] is None  # todavía no se exporta ningún lote


def test_reusing_same_filename_in_a_new_batch_is_not_blocked(qapp, db, tmp_path):
    """El histórico nunca bloquea: el mismo nombre puede volver a subirse el mes
    siguiente. Sólo se avisa si se repite DENTRO del mismo lote sin exportar."""
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote_mensual.xlsx"
    _write_valid_file(path)

    # Primera "sesión": se sube y se exporta (limpia self._rows/_source_filenames).
    view = RequerimientosImportView(agente)
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()
    assert len(view._rows) == 1

    with patch(
        "app.ui.agente.requerimientos_import_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch("app.ui.agente.requerimientos_import_view.QMessageBox.information"):
        view._on_export()
    assert view._rows == []
    assert view._source_filenames == []

    # Segunda "sesión" (nuevo lote), mismo nombre de archivo: no debe avisar de duplicado.
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ), patch("app.ui.agente.requerimientos_import_view.QMessageBox.question") as mock_question:
        view._on_select_files()

    mock_question.assert_not_called()
    assert len(view._rows) == 1

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM imported_files WHERE agente_id = ? AND original_filename = ?",
        (agente.id, "lote_mensual.xlsx"),
    ).fetchall()
    assert len(rows) == 2  # ambas subidas quedaron en el histórico
    assert rows[0]["batch_id"] is not None  # la primera sí quedó ligada a su lote exportado
    assert rows[1]["batch_id"] is None  # la segunda todavía no se exporta


def test_export_filename_follows_lista_del_convention(qapp, db, tmp_path):
    from app.utils.paths import exports_dir

    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosImportView(agente)
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_import_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch("app.ui.agente.requerimientos_import_view.QMessageBox.information"):
        view._on_export()

    fecha = datetime.now().strftime("%d_%m_%Y")
    expected = exports_dir() / f"LISTA DEL {fecha} Abogado Uno.mcdiep"
    assert expected.exists()


def test_export_without_certificate_is_blocked(qapp, db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosImportView(agente)
    with patch(
        "app.ui.agente.requerimientos_import_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch("app.ui.agente.requerimientos_import_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.agente.requerimientos_import_view.CertificateConfirmDialog"
    ) as mock_confirm_cls:
        view._on_export()

    mock_warning.assert_called_once()
    mock_confirm_cls.assert_not_called()
    assert view._rows  # no se limpió: no se exportó nada
