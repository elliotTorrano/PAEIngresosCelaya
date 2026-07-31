from app.auth.cert_auth import GENERIC_FAILURE_MESSAGE, verify_certificate_file
from app.auth.crypto_certs import generate_certificate_bundle
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories.users import User


def _make_user(cert_public_pem, cert_serial):
    return User(
        id=1, username="jperez", role=ROLE_ADMINISTRADOR, full_name="Juan Pérez", email="j@j.com",
        auth_type=AUTH_TYPE_CERTIFICADO, password_hash=None, password_salt=None,
        cert_public_pem=cert_public_pem, cert_serial=cert_serial, cert_file_path=None,
        recovery_code_hash=None, recovery_code_salt=None,
        must_change_password=False, active=True,
    )


def test_verify_certificate_file_success(tmp_path):
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )
    pfx_path = tmp_path / "cert.pfx"
    pfx_path.write_bytes(pfx_bytes)

    user = _make_user(cert_public_pem, cert_serial)
    ok, message = verify_certificate_file(user, pfx_path, "clave-segura")

    assert ok is True
    assert message == ""


def test_verify_certificate_file_wrong_password(tmp_path):
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )
    pfx_path = tmp_path / "cert.pfx"
    pfx_path.write_bytes(pfx_bytes)

    user = _make_user(cert_public_pem, cert_serial)
    ok, message = verify_certificate_file(user, pfx_path, "clave-incorrecta")

    assert ok is False
    assert message


def test_verify_certificate_file_wrong_user(tmp_path):
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )
    pfx_path = tmp_path / "cert.pfx"
    pfx_path.write_bytes(pfx_bytes)

    # Usuario con un serial distinto (como si el certificado fuera de otra cuenta).
    user = _make_user(cert_public_pem, "otro-serial")
    ok, message = verify_certificate_file(user, pfx_path, "clave-segura")

    assert ok is False
    assert message


def test_wrong_password_and_wrong_owner_give_the_identical_generic_message(tmp_path):
    """No debe ser posible distinguir, por el mensaje, si se probó la
    contraseña CORRECTA de un certificado que simplemente no es el de esta
    cuenta, de una contraseña INCORRECTA cualquiera -- eso le confirmaría a
    quien prueba un .pfx ajeno que acertó su contraseña."""
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )
    pfx_path = tmp_path / "cert.pfx"
    pfx_path.write_bytes(pfx_bytes)

    wrong_password_user = _make_user(cert_public_pem, cert_serial)
    _, wrong_password_message = verify_certificate_file(wrong_password_user, pfx_path, "clave-incorrecta")

    wrong_owner_user = _make_user(cert_public_pem, "otro-serial")
    _, wrong_owner_message = verify_certificate_file(wrong_owner_user, pfx_path, "clave-segura")

    assert wrong_password_message == wrong_owner_message == GENERIC_FAILURE_MESSAGE
