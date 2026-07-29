"""Generación de certificado en el primer login de un usuario de rol certificado."""

from __future__ import annotations

from pathlib import Path

from app.auth.crypto_certs import generate_certificate_bundle
from app.db.repositories import users as users_repo


def enroll_certificate(user: users_repo.User, *, password: str, save_path: Path) -> None:
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=user.username, full_name=user.full_name, password=password
    )
    save_path.write_bytes(pfx_bytes)
    users_repo.set_certificate(user.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
