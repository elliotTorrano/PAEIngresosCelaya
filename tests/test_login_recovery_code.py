from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog

from app.auth.enrollment import enroll_certificate
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.ui.login.login_window import LoginWindow


def _make_user_with_cert(username, role, tmp_path):
    user = users_repo.create_user(
        username=username, role=role, full_name=username, email=f"{username}@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    enroll_certificate(user, password="clave-segura", save_path=tmp_path / f"{username}.pfx")
    return users_repo.get_by_id(user.id)


def test_recovery_button_visible_only_for_roles_with_code(qapp, db, tmp_path):
    admin = _make_user_with_cert("admin", ROLE_ADMINISTRADOR, tmp_path)
    agente = _make_user_with_cert("agente1", ROLE_AGENTE_PAE, tmp_path)

    window = LoginWindow()

    window.username_input.setText(admin.username)
    window._on_continue()
    assert window.stack.currentIndex() == 2
    # El widget nunca se muestra (headless): isVisible() depende de la cadena
    # de ancestros mostrados, así que se compara el flag explícito de
    # visibilidad en vez de isVisible().
    assert not window.recovery_code_btn.isHidden()

    window._on_back_to_username()
    window.username_input.setText(agente.username)
    window._on_continue()
    assert window.stack.currentIndex() == 2
    assert window.recovery_code_btn.isHidden()


def test_recover_with_code_reenrolls_after_successful_recovery(qapp, db, tmp_path):
    admin = _make_user_with_cert("admin", ROLE_ADMINISTRADOR, tmp_path)
    window = LoginWindow()
    window._user = admin

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog.recovered = True

    with patch(
        "app.ui.login.login_window.RecoveryCodeRecoveryDialog", return_value=mock_dialog
    ), patch("app.ui.login.login_window.QMessageBox.information"), patch.object(
        LoginWindow, "_run_enrollment"
    ) as mock_run_enrollment:
        window._on_recover_with_code()

    mock_run_enrollment.assert_called_once()
    assert mock_run_enrollment.call_args.args[0].id == admin.id


def test_recover_with_code_does_nothing_when_dialog_cancelled(qapp, db, tmp_path):
    admin = _make_user_with_cert("admin", ROLE_ADMINISTRADOR, tmp_path)
    window = LoginWindow()
    window._user = admin

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
    mock_dialog.recovered = False

    with patch(
        "app.ui.login.login_window.RecoveryCodeRecoveryDialog", return_value=mock_dialog
    ), patch.object(LoginWindow, "_run_enrollment") as mock_run_enrollment:
        window._on_recover_with_code()

    mock_run_enrollment.assert_not_called()
