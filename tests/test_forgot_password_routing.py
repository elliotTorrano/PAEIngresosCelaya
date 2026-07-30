from unittest.mock import patch

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo
from app.ui.login.forgot_password_dialog import ForgotPasswordDialog


def _make_admin_and_super():
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="admin@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    su = users_repo.create_user(
        username="super1", role=ROLE_SUPERUSUARIO, full_name="Super", email="super@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    return admin, su


def test_administrador_request_routes_to_superusuario(qapp, db, tmp_path):
    admin, su = _make_admin_and_super()
    dialog = ForgotPasswordDialog()
    dialog.username_input.setText(admin.username)

    with patch(
        "app.ui.login.forgot_password_dialog.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
    ), patch(
        "app.ui.login.forgot_password_dialog.recovery.open_email_client"
    ) as mock_email, patch("app.ui.login.forgot_password_dialog.QMessageBox.information"):
        dialog._on_submit()

    mock_email.assert_called_once()
    assert mock_email.call_args.kwargs["to_email"] == su.email


def test_superusuario_request_still_routes_to_administrador(qapp, db, tmp_path):
    admin, su = _make_admin_and_super()
    dialog = ForgotPasswordDialog()
    dialog.username_input.setText(su.username)

    with patch(
        "app.ui.login.forgot_password_dialog.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
    ), patch(
        "app.ui.login.forgot_password_dialog.recovery.open_email_client"
    ) as mock_email, patch("app.ui.login.forgot_password_dialog.QMessageBox.information"):
        dialog._on_submit()

    mock_email.assert_called_once()
    assert mock_email.call_args.kwargs["to_email"] == admin.email


def test_administrador_request_without_superusuario_shows_critical_and_no_email(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="admin@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    dialog = ForgotPasswordDialog()
    dialog.username_input.setText(admin.username)

    with patch("app.ui.login.forgot_password_dialog.QMessageBox.critical") as mock_critical, patch(
        "app.ui.login.forgot_password_dialog.recovery.open_email_client"
    ) as mock_email:
        dialog._on_submit()

    mock_critical.assert_called_once()
    mock_email.assert_not_called()
