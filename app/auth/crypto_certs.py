"""Certificados digitales autofirmados (estilo e.firma) para súper-usuario, administrador y agentes.

Cada usuario guarda un único archivo .pfx (llave privada + certificado, protegido
con una contraseña que él mismo elige). La base de datos sólo guarda la parte
pública del certificado, nunca la llave privada.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

CERT_VALIDITY_YEARS = 10


class InvalidCertificateFile(Exception):
    """El archivo .pfx no se pudo abrir (contraseña incorrecta o archivo dañado/no es un certificado)."""


def generate_certificate_bundle(*, username: str, full_name: str, password: str) -> tuple[bytes, str, str]:
    """Genera una llave RSA-2048 + certificado autofirmado para `username`.

    Devuelve (pfx_bytes, cert_public_pem, cert_serial_hex).
    `pfx_bytes` es el archivo protegido con `password` que el usuario debe guardar
    donde él elija; sólo `cert_public_pem`/`cert_serial_hex` se guardan en la BD.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, username),
            x509.NameAttribute(NameOID.PSEUDONYM, full_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Sistema PAE"),
        ]
    )

    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365 * CERT_VALIDITY_YEARS))
        .sign(private_key, hashes.SHA256())
    )

    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=username.encode("utf-8"),
        key=private_key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )

    cert_public_pem = certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    cert_serial = format(certificate.serial_number, "x")

    return pfx_bytes, cert_public_pem, cert_serial


def load_bundle(pfx_bytes: bytes, password: str):
    """Abre el .pfx del usuario y devuelve (private_key, certificate)."""
    try:
        private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_bytes, password.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise InvalidCertificateFile("Archivo de certificado o contraseña inválidos.") from exc
    if private_key is None or certificate is None:
        raise InvalidCertificateFile("El archivo no contiene una llave/certificado válidos.")
    return private_key, certificate


def sign_challenge(private_key, challenge: bytes) -> bytes:
    return private_key.sign(challenge, padding.PKCS1v15(), hashes.SHA256())


def verify_challenge(cert_public_pem: str, challenge: bytes, signature: bytes) -> bool:
    certificate = x509.load_pem_x509_certificate(cert_public_pem.encode("utf-8"))
    public_key = certificate.public_key()
    try:
        public_key.verify(signature, challenge, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def cert_matches_serial(certificate: x509.Certificate, expected_serial_hex: str) -> bool:
    return format(certificate.serial_number, "x") == expected_serial_hex
