from unittest.mock import patch

from PySide6.QtWidgets import QLineEdit

from app.auth.enrollment import enroll_certificate
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories import users as users_repo
from app.ui.login.recovery_code_dialog import RecoveryCodeDisplayDialog, RecoveryCodeRecoveryDialog


def _make_admin_with_cert(tmp_path):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    recovery_code = enroll_certificate(admin, password="clave-segura", save_path=tmp_path / "admin.pfx")
    return users_repo.get_by_id(admin.id), recovery_code


def test_display_dialog_shows_code_readonly(qapp):
    dialog = RecoveryCodeDisplayDialog("AAAA-BBBB-CCCC-DDDD")
    code_edit = dialog.findChild(QLineEdit)
    assert code_edit.text() == "AAAA-BBBB-CCCC-DDDD"
    assert code_edit.isReadOnly()


def test_correct_code_clears_certificate(qapp, db, tmp_path):
    admin, code = _make_admin_with_cert(tmp_path)
    dialog = RecoveryCodeRecoveryDialog(admin)
    dialog.code_input.setText(code)

    dialog._on_confirm()

    assert dialog.recovered is True
    refreshed = users_repo.get_by_id(admin.id)
    assert not users_repo.has_certificate(refreshed)


def test_wrong_code_does_not_clear_certificate(qapp, db, tmp_path):
    admin, _code = _make_admin_with_cert(tmp_path)
    dialog = RecoveryCodeRecoveryDialog(admin)
    dialog.code_input.setText("ZZZZ-ZZZZ-ZZZZ-ZZZZ")

    with patch("app.ui.login.recovery_code_dialog.QMessageBox.warning"):
        dialog._on_confirm()

    assert dialog.recovered is False
    refreshed = users_repo.get_by_id(admin.id)
    assert users_repo.has_certificate(refreshed)


def test_empty_code_warns_and_does_nothing(qapp, db, tmp_path):
    admin, _code = _make_admin_with_cert(tmp_path)
    dialog = RecoveryCodeRecoveryDialog(admin)
    dialog.code_input.setText("   ")

    with patch("app.ui.login.recovery_code_dialog.QMessageBox.warning") as mock_warning:
        dialog._on_confirm()

    mock_warning.assert_called_once()
    assert dialog.recovered is False
