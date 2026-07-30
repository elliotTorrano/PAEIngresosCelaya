from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog, QPushButton

from app.auth.enrollment import enroll_certificate
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


def _find_button(view, text) -> QPushButton:
    for btn in view.findChildren(QPushButton):
        if btn.text() == text:
            return btn
    raise AssertionError(f"No se encontró el botón '{text}'")


def test_generate_new_certificate_requires_confirmation(qapp, db, tmp_path):
    admin = _make_admin_with_cert(tmp_path)
    view = AccountSettingsView(admin)
    button = _find_button(view, "Generar nuevo certificado")

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Rejected

    with patch("app.ui.admin.account_settings_view.CertificateConfirmDialog", return_value=mock_confirm):
        button.click()

    assert users_repo.has_certificate(users_repo.get_by_id(admin.id))


def test_generate_new_certificate_clears_after_confirmation(qapp, db, tmp_path):
    admin = _make_admin_with_cert(tmp_path)
    view = AccountSettingsView(admin)
    button = _find_button(view, "Generar nuevo certificado")

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Accepted

    with patch("app.ui.admin.account_settings_view.CertificateConfirmDialog", return_value=mock_confirm), patch(
        "app.ui.admin.account_settings_view.QMessageBox.information"
    ):
        button.click()

    assert not users_repo.has_certificate(users_repo.get_by_id(admin.id))


def test_generate_new_certificate_without_certificate_warns(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    view = AccountSettingsView(admin)
    button = _find_button(view, "Generar nuevo certificado")

    with patch("app.ui.admin.account_settings_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.admin.account_settings_view.CertificateConfirmDialog"
    ) as mock_confirm_cls:
        button.click()

    mock_warning.assert_called_once()
    mock_confirm_cls.assert_not_called()
