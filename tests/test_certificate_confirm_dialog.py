from unittest.mock import patch

from PySide6.QtWidgets import QLabel

from app.auth.crypto_certs import generate_certificate_bundle
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories import users as users_repo
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog


def _make_admin_with_cert(tmp_path):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=admin.username, full_name=admin.full_name, password="clave-segura"
    )
    users_repo.set_certificate(admin.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    pfx_path = tmp_path / "admin.pfx"
    pfx_path.write_bytes(pfx_bytes)
    return users_repo.get_by_id(admin.id), pfx_path


def test_correct_certificate_exposes_private_key(qapp, db, tmp_path):
    admin, pfx_path = _make_admin_with_cert(tmp_path)
    dialog = CertificateConfirmDialog(admin)
    dialog._cert_path = str(pfx_path)
    dialog.password_input.setText("clave-segura")

    dialog._on_confirm()

    assert dialog.result() == 1  # QDialog.DialogCode.Accepted
    assert dialog.private_key is not None


def test_wrong_password_does_not_expose_private_key(qapp, db, tmp_path):
    admin, pfx_path = _make_admin_with_cert(tmp_path)
    dialog = CertificateConfirmDialog(admin)
    dialog._cert_path = str(pfx_path)
    dialog.password_input.setText("clave-incorrecta")

    with patch("app.ui.widgets.certificate_confirm_dialog.QMessageBox.warning") as mock_warning:
        dialog._on_confirm()

    mock_warning.assert_called_once()
    assert dialog.private_key is None
    assert dialog.result() != 1


def test_missing_certificate_path_warns(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    dialog = CertificateConfirmDialog(admin)

    with patch("app.ui.widgets.certificate_confirm_dialog.QMessageBox.warning") as mock_warning:
        dialog._on_confirm()

    mock_warning.assert_called_once()
    assert dialog.private_key is None


def test_custom_message_is_shown_instead_of_default(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    dialog = CertificateConfirmDialog(admin, message="Mensaje de prueba a medida.")

    label_texts = [w.text() for w in dialog.findChildren(QLabel)]
    assert "Mensaje de prueba a medida." in label_texts
    assert not any("cambiar estos datos" in text for text in label_texts)


def test_default_message_is_shown_when_none_given(qapp, db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    dialog = CertificateConfirmDialog(admin)

    label_texts = [w.text() for w in dialog.findChildren(QLabel)]
    assert any("cambiar estos datos" in text for text in label_texts)
