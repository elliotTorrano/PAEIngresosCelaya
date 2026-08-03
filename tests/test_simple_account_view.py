from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog, QPushButton

from app.auth.enrollment import enroll_certificate
from app.auth.passwords import hash_password, verify_password
from app.config import (
    AUTH_TYPE_CERTIFICADO,
    AUTH_TYPE_PASSWORD,
    DUMMY_ABOGADO_USERNAME,
    DUMMY_AGENTE_USERNAME,
    ROLE_ABOGADO,
    ROLE_AGENTE_PAE,
)
from app.db.repositories import users as users_repo
from app.ui.widgets.simple_account_view import SimpleAccountView


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="viejo@example.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_agente_with_cert(tmp_path):
    agente = _make_agente()
    enroll_certificate(agente, password="clave-segura", save_path=tmp_path / "agente1.pfx")
    return users_repo.get_by_id(agente.id)


def _make_abogado():
    pwd_hash, salt = hash_password("clave-actual")
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash=pwd_hash, password_salt=salt,
    )


def _has_button(view, text) -> bool:
    return any(btn.text() == text for btn in view.findChildren(QPushButton))


def test_save_empty_email_warns_and_does_not_update(qapp, db):
    agente = _make_agente()
    view = SimpleAccountView(agente)
    view.email_input.setText("   ")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.widgets.simple_account_view.users_repo.update_email"
    ) as mock_update:
        view._on_save()

    mock_warning.assert_called_once()
    mock_update.assert_not_called()


def test_save_valid_email_updates_and_confirms(qapp, db):
    agente = _make_agente()
    view = SimpleAccountView(agente)
    view.email_input.setText("nuevo@example.com")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.information") as mock_info:
        view._on_save()

    mock_info.assert_called_once()
    refreshed = users_repo.get_by_id(agente.id)
    assert refreshed.email == "nuevo@example.com"
    assert refreshed.username == "agente1"
    assert refreshed.full_name == "Agente Uno"


def test_agente_view_shows_certificate_section_not_password(qapp, db, tmp_path):
    agente = _make_agente_with_cert(tmp_path)
    view = SimpleAccountView(agente)

    assert _has_button(view, "Generar nuevo certificado")
    assert not hasattr(view, "current_password_input")


def test_agente_generate_new_certificate_requires_confirmation(qapp, db, tmp_path):
    agente = _make_agente_with_cert(tmp_path)
    view = SimpleAccountView(agente)

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Rejected

    with patch("app.ui.widgets.simple_account_view.CertificateConfirmDialog", return_value=mock_confirm):
        view._on_generate_new_certificate()

    assert users_repo.has_certificate(users_repo.get_by_id(agente.id))


def test_agente_generate_new_certificate_clears_after_confirmation(qapp, db, tmp_path):
    agente = _make_agente_with_cert(tmp_path)
    view = SimpleAccountView(agente)

    mock_confirm = MagicMock()
    mock_confirm.exec.return_value = QDialog.DialogCode.Accepted

    with patch("app.ui.widgets.simple_account_view.CertificateConfirmDialog", return_value=mock_confirm), patch(
        "app.ui.widgets.simple_account_view.QMessageBox.information"
    ):
        view._on_generate_new_certificate()

    assert not users_repo.has_certificate(users_repo.get_by_id(agente.id))


def test_abogado_view_shows_password_section_not_certificate(qapp, db):
    abogado = _make_abogado()
    view = SimpleAccountView(abogado)

    assert hasattr(view, "current_password_input")
    assert not _has_button(view, "Generar nuevo certificado")


def test_abogado_change_password_wrong_current_password(qapp, db):
    abogado = _make_abogado()
    view = SimpleAccountView(abogado)
    view.current_password_input.setText("incorrecta")
    view.new_password_input.setText("nueva-clave")
    view.confirm_password_input.setText("nueva-clave")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.warning") as mock_warning:
        view._on_change_password()

    mock_warning.assert_called_once()
    refreshed = users_repo.get_by_id(abogado.id)
    assert verify_password("clave-actual", refreshed.password_hash, refreshed.password_salt)


def test_abogado_change_password_success(qapp, db):
    abogado = _make_abogado()
    view = SimpleAccountView(abogado)
    view.current_password_input.setText("clave-actual")
    view.new_password_input.setText("nueva-clave-6")
    view.confirm_password_input.setText("nueva-clave-6")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.information") as mock_info:
        view._on_change_password()

    mock_info.assert_called_once()
    refreshed = users_repo.get_by_id(abogado.id)
    assert verify_password("nueva-clave-6", refreshed.password_hash, refreshed.password_salt)


def test_abogado_change_password_mismatch(qapp, db):
    abogado = _make_abogado()
    view = SimpleAccountView(abogado)
    view.current_password_input.setText("clave-actual")
    view.new_password_input.setText("nueva-clave-6")
    view.confirm_password_input.setText("otra-clave-6")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.warning") as mock_warning:
        view._on_change_password()

    mock_warning.assert_called_once()


def test_dummy_agente_view_hides_email_and_certificate_controls(qapp, db):
    pwd_hash, salt = hash_password("dummy12345")
    dummy = users_repo.create_user(
        username=DUMMY_AGENTE_USERNAME, role=ROLE_AGENTE_PAE, full_name="Agente del PAE (prueba)",
        email=None, auth_type=AUTH_TYPE_PASSWORD, password_hash=pwd_hash, password_salt=salt,
    )
    view = SimpleAccountView(dummy)

    assert not hasattr(view, "email_input")
    assert not hasattr(view, "current_password_input")
    assert not _has_button(view, "Guardar correo")
    assert not _has_button(view, "Generar nuevo certificado")


def test_dummy_abogado_view_hides_password_controls(qapp, db):
    pwd_hash, salt = hash_password("dummy12345")
    dummy = users_repo.create_user(
        username=DUMMY_ABOGADO_USERNAME, role=ROLE_ABOGADO, full_name="Abogado (prueba)",
        email=None, auth_type=AUTH_TYPE_PASSWORD, password_hash=pwd_hash, password_salt=salt,
    )
    view = SimpleAccountView(dummy)

    assert not hasattr(view, "current_password_input")
    assert not _has_button(view, "Cambiar contraseña")


def test_abogado_change_password_too_short(qapp, db):
    abogado = _make_abogado()
    view = SimpleAccountView(abogado)
    view.current_password_input.setText("clave-actual")
    view.new_password_input.setText("abc")
    view.confirm_password_input.setText("abc")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.warning") as mock_warning:
        view._on_change_password()

    mock_warning.assert_called_once()
