import os

import pytest

from app.auth.crypto_certs import (
    InvalidCertificateFile,
    cert_matches_serial,
    generate_certificate_bundle,
    load_bundle,
    sign_challenge,
    verify_challenge,
)


def test_generate_load_and_verify_roundtrip():
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )

    private_key, certificate = load_bundle(pfx_bytes, "clave-segura")
    assert cert_matches_serial(certificate, cert_serial)

    challenge = os.urandom(32)
    signature = sign_challenge(private_key, challenge)
    assert verify_challenge(cert_public_pem, challenge, signature)


def test_wrong_password_raises():
    pfx_bytes, _, _ = generate_certificate_bundle(username="jperez", full_name="Juan Pérez", password="clave-segura")
    with pytest.raises(InvalidCertificateFile):
        load_bundle(pfx_bytes, "clave-incorrecta")


def test_verify_fails_with_wrong_challenge():
    pfx_bytes, cert_public_pem, _ = generate_certificate_bundle(
        username="jperez", full_name="Juan Pérez", password="clave-segura"
    )
    private_key, _ = load_bundle(pfx_bytes, "clave-segura")
    signature = sign_challenge(private_key, b"challenge-a")
    assert not verify_challenge(cert_public_pem, b"challenge-b", signature)
