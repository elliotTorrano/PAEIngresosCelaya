from datetime import datetime
from unittest.mock import MagicMock, patch

import openpyxl
from PySide6.QtWidgets import QDialog, QMessageBox

from app.auth.cert_auth import GENERIC_FAILURE_MESSAGE
from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog


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


def _make_agente_abogado_with_pfx(tmp_path):
    """Igual que _make_agente_abogado, pero además deja el .pfx real del Agente
    escrito en disco -- para pruebas que ejercitan CertificateConfirmDialog de
    verdad (contraseña incorrecta, certificado de otra cuenta), no simulado."""
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-agente"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    agente = users_repo.get_by_id(agente.id)
    agente_pfx_path = tmp_path / "agente1.pfx"
    agente_pfx_path.write_bytes(pfx_bytes)

    users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    return agente, agente_pfx_path


def _mock_confirm_dialog(private_key):
    mock = MagicMock()
    mock.exec.return_value = QDialog.DialogCode.Accepted
    mock.private_key = private_key
    return mock


def _make_confirm_exec(pfx_path, password):
    """Reemplaza CertificateConfirmDialog.exec por una versión que llena los
    campos y llama _on_confirm() de verdad (sin entrar al loop modal real de
    Qt, que se quedaría esperando para siempre en las pruebas) -- así se
    ejercita la verificación real de contraseña/certificado tal como la
    probó el usuario a mano, en vez de simularla con un mock."""

    def _exec(self):
        self._cert_path = str(pfx_path)
        self.password_input.setText(password)
        self._on_confirm()
        return self.result()

    return _exec


def test_selecting_a_file_logs_it_immediately(qapp, db, tmp_path):
    agente, _private_key = _make_agente_abogado()
    path = tmp_path / "lote_julio.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
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
    from app.utils.paths import exports_dir

    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote_mensual.xlsx"
    _write_valid_file(path)

    # Primera "sesión": se sube y se exporta (limpia self._rows/_source_filenames).
    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()
    assert len(view._rows) == 1

    with patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()
    assert view._rows == []
    assert view._source_filenames == []

    # Segunda "sesión" (nuevo lote), mismo nombre de archivo: no debe avisar de duplicado.
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.question") as mock_question:
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

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(exports_dir()),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
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

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog"
    ) as mock_confirm_cls:
        view._on_export()

    mock_warning.assert_called_once()
    mock_confirm_cls.assert_not_called()
    assert view._rows  # no se limpió: no se exportó nada


def test_export_aborts_when_certificate_confirmation_rejected(qapp, db, tmp_path):
    agente, _private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog", return_value=mock_dialog
    ), patch("app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory") as mock_folder_dialog:
        view._on_export()

    mock_folder_dialog.assert_not_called()  # nunca debió llegar a pedir carpeta
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0
    assert view._rows  # no se limpió: no se exportó nada


def test_export_blocked_with_wrong_password(qapp, db, tmp_path):
    """Reproduce la prueba manual: certificado real del Agente, pero con la
    contraseña incorrecta -- debe rechazarse sin exportar nada, sin siquiera
    llegar a preguntar la carpeta de destino."""
    agente, agente_pfx_path = _make_agente_abogado_with_pfx(tmp_path)
    source_path = tmp_path / "lote.xlsx"
    _write_valid_file(source_path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    with patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(agente_pfx_path, "clave-incorrecta")
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.widgets.certificate_confirm_dialog.QMessageBox.warning") as mock_warning, patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory"
    ) as mock_folder_dialog:
        view._on_export()

    mock_warning.assert_called_once()
    assert mock_warning.call_args[0][2] == GENERIC_FAILURE_MESSAGE
    mock_folder_dialog.assert_not_called()
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0
    assert view._rows


def test_export_blocked_with_certificate_from_another_account(qapp, db, tmp_path):
    """Reproduce la prueba manual: un certificado válido (contraseña correcta)
    pero de OTRA cuenta -- debe rechazarse por no corresponder al Agente que
    está exportando, sin exportar nada."""
    agente, _agente_pfx_path = _make_agente_abogado_with_pfx(tmp_path)

    other = users_repo.create_user(
        username="otro_agente", role=ROLE_AGENTE_PAE, full_name="Otro Agente", email="o@o.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    other_pfx_bytes, other_pem, other_serial = generate_certificate_bundle(
        username=other.username, full_name=other.full_name, password="clave-otro"
    )
    users_repo.set_certificate(other.id, cert_public_pem=other_pem, cert_serial=other_serial)
    other_pfx_path = tmp_path / "otro.pfx"
    other_pfx_path.write_bytes(other_pfx_bytes)

    source_path = tmp_path / "lote.xlsx"
    _write_valid_file(source_path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    with patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(other_pfx_path, "clave-otro")
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.widgets.certificate_confirm_dialog.QMessageBox.warning") as mock_warning, patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory"
    ) as mock_folder_dialog:
        view._on_export()

    mock_warning.assert_called_once()
    # Mensaje genérico deliberado: no debe distinguir "contraseña correcta,
    # certificado ajeno" de "contraseña incorrecta" (ver test_export_blocked_with_wrong_password).
    assert mock_warning.call_args[0][2] == GENERIC_FAILURE_MESSAGE
    mock_folder_dialog.assert_not_called()
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0


def test_export_succeeds_with_correct_password_and_certificate(qapp, db, tmp_path):
    agente, agente_pfx_path = _make_agente_abogado_with_pfx(tmp_path)
    source_path = tmp_path / "lote.xlsx"
    _write_valid_file(source_path)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    with patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(agente_pfx_path, "clave-agente")
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    matches = list(dest_folder.glob("LISTA DEL *.mcdiep"))
    assert len(matches) == 1


def test_export_succeeded_batch_appears_in_list_batches_for_agente(qapp, db, tmp_path):
    agente, agente_pfx_path = _make_agente_abogado_with_pfx(tmp_path)
    source_path = tmp_path / "lote.xlsx"
    _write_valid_file(source_path)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    with patch.object(
        CertificateConfirmDialog, "exec", _make_confirm_exec(agente_pfx_path, "clave-agente")
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    batches = req_repo.list_batches_for_agente(agente.id)
    assert len(batches) == 1
    assert batches[0]["exported_agente_path"] is not None
    assert batches[0]["abogado_nombre"] == "Abogado Uno"


def test_export_cancelled_folder_picker_creates_no_batch(qapp, db, tmp_path):
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory", return_value=""
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        view._on_export()

    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0
    assert view._rows  # no se limpió: no se exportó nada


# --- Lista de archivos visible + confirmación antes de exportar ----------------------

def test_files_label_lists_loaded_excel_files(qapp, db, tmp_path):
    agente, _private_key = _make_agente_abogado()
    path = tmp_path / "lote_julio.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)
    assert "ninguno" in view.files_label.text()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    assert "lote_julio.xlsx" in view.files_label.text()


def test_export_rejected_confirmation_keeps_loaded_rows(qapp, db, tmp_path):
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.No,
    ), patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog"
    ) as mock_confirm_cls:
        view._on_export()

    mock_confirm_cls.assert_not_called()
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0
    assert view._rows  # no se limpió: sigue lo cargado
    assert view._source_filenames == ["lote.xlsx"]


def test_export_confirmation_shows_file_list(qapp, db, tmp_path):
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote_agosto.xlsx"
    _write_valid_file(path)

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ) as mock_question, patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(tmp_path),
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    mock_question.assert_called_once()
    assert "lote_agosto.xlsx" in mock_question.call_args[0][2]


# --- Confirmar sobrescritura si el archivo ya existe ----------------------------------

def test_export_overwrite_confirmation_declined_keeps_existing_file(qapp, db, tmp_path):
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    fecha = datetime.now().strftime("%d_%m_%Y")
    existing = dest_folder / f"LISTA DEL {fecha} Abogado Uno.mcdiep"
    existing.write_bytes(b"contenido previo")

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        side_effect=[QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No],
    ), patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ):
        view._on_export()

    assert existing.read_bytes() == b"contenido previo"
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 0
    assert view._rows  # no se limpió: no se exportó nada


def test_export_overwrite_confirmed_replaces_file(qapp, db, tmp_path):
    agente, private_key = _make_agente_abogado()
    path = tmp_path / "lote.xlsx"
    _write_valid_file(path)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    fecha = datetime.now().strftime("%d_%m_%Y")
    existing = dest_folder / f"LISTA DEL {fecha} Abogado Uno.mcdiep"
    existing.write_bytes(b"contenido previo")

    view = RequerimientosGenerarView(agente)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch(
        "app.ui.agente.requerimientos_generar_view.CertificateConfirmDialog",
        return_value=_mock_confirm_dialog(private_key),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    assert existing.read_bytes() != b"contenido previo"
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM requerimiento_batches").fetchone()["n"] == 1


# --- Columnas redimensionables ---------------------------------------------------------

def test_tables_use_interactive_resize_mode(qapp, db):
    from PySide6.QtWidgets import QHeaderView

    agente, _private_key = _make_agente_abogado()
    view = RequerimientosGenerarView(agente)

    assert view.table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert view.table.horizontalHeader().stretchLastSection() is True
