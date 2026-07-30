from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.ui.login.login_window import LoginWindow


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_run_enrollment_deferred_closes_login_window(qapp, db):
    agente = _make_agente()
    window = LoginWindow()

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
    mock_dialog.deferred = True

    with patch("app.ui.login.login_window.EnrollmentDialog", return_value=mock_dialog):
        window._run_enrollment(agente)

    assert window.result() == QDialog.DialogCode.Rejected


def test_run_enrollment_cancelled_without_defer_returns_to_username_page(qapp, db):
    agente = _make_agente()
    window = LoginWindow()
    window.stack.setCurrentIndex(2)

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
    mock_dialog.deferred = False

    with patch("app.ui.login.login_window.EnrollmentDialog", return_value=mock_dialog):
        window._run_enrollment(agente)

    assert window.stack.currentIndex() == 0
