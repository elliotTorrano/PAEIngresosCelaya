"""Generación de certificado en el primer login de un usuario de rol certificado."""

from __future__ import annotations

from pathlib import Path

from app.auth.crypto_certs import generate_certificate_bundle
from app.auth.recovery_codes import ROLES_WITH_RECOVERY_CODE, generate_recovery_code, hash_recovery_code
from app.db.repositories import users as users_repo


def enroll_certificate(user: users_repo.User, *, password: str, save_path: Path) -> str | None:
    """Genera el certificado y lo guarda en `save_path`. Para Súper-usuario y
    Administrador, además genera y guarda un nuevo código de respaldo (invalida
    cualquier código anterior) y lo devuelve para mostrarlo una sola vez; para
    los demás roles devuelve None."""
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=user.username, full_name=user.full_name, password=password
    )
    save_path.write_bytes(pfx_bytes)
    users_repo.set_certificate(user.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)

    if user.role not in ROLES_WITH_RECOVERY_CODE:
        return None

    recovery_code = generate_recovery_code()
    code_hash, code_salt = hash_recovery_code(recovery_code)
    users_repo.set_recovery_code(user.id, recovery_code_hash=code_hash, recovery_code_salt=code_salt)
    return recovery_code
