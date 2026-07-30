from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog, QPushButton

from app.auth.enrollment import enroll_certificate
from app.auth.recovery_codes import verify_recovery_code
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories import users as users_repo
from app.ui.admin.account_settings_view import AccountSettingsView


def _make_admin_with_cert(tmp_path):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    enroll_certificate(admin, password="clave-segura", save_path=tmp_path / "admin.pfx")
    return users_repo.get_by_id(admin.id)


def _find_recovery_button(view) -> QPushButton:
    for btn in view.findChildren(QPushButton):
        if btn.text() == "Generar nuevo código de respaldo":
            return btn
    raise AssertionError("No se encontró el botón de código de respaldo")


def test_generate_recovery_code_requires_certificate_confirmation(qapp, db, tmp_path):
    admin = _make_admin_with_cert(tmp_path)
    view = AccountSettingsView(admin)
    button = _find_recovery_button(view)
    old_hash = admin.recovery_code_hash

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Rejected

    with patch(
        "app.ui.admin.account_settings_view.CertificateConfirmDialog", return_value=mock_confirm
    ), patch("app.ui.admin.account_settings_view.RecoveryCodeDisplayDialog") as mock_display_cls:
        button.click()

    mock_display_cls.assert_not_called()
    assert users_repo.get_by_id(admin.id).recovery_code_hash == old_hash


def test_generate_recovery_code_rotates_and_shows_new_code(qapp, db, tmp_path):
    admin = _make_admin_with_cert(tmp_path)
    view = AccountSettingsView(admin)
    button = _find_recovery_button(view)
    old_hash = users_repo.get_by_id(admin.id).recovery_code_hash

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Accepted

    shown_codes = []

    def _capture_display(code, parent=None):
        shown_codes.append(code)
        mock = MagicMock()
        mock.exec.return_value = QDialog.DialogCode.Accepted
        return mock

    with patch(
        "app.ui.admin.account_settings_view.CertificateConfirmDialog", return_value=mock_confirm
    ), patch(
        "app.ui.admin.account_settings_view.RecoveryCodeDisplayDialog", side_effect=_capture_display
    ):
        button.click()

    assert len(shown_codes) == 1
    refreshed = users_repo.get_by_id(admin.id)
    assert refreshed.recovery_code_hash != old_hash
    assert verify_recovery_code(refreshed, shown_codes[0]) is True


def test_generate_recovery_code_without_certificate_warns(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    view = AccountSettingsView(admin)
    button = _find_recovery_button(view)

    with patch("app.ui.admin.account_settings_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.admin.account_settings_view.CertificateConfirmDialog"
    ) as mock_confirm_cls:
        button.click()

    mock_warning.assert_called_once()
    mock_confirm_cls.assert_not_called()
