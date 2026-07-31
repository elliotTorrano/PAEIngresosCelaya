"""Verificación de un archivo .pfx contra el certificado vigente de un usuario.

Se usa tanto en el login como para re-confirmar identidad antes de operaciones
sensibles (p. ej. cambiar los datos del súper-usuario o del Administrador).
"""

from __future__ import annotations

import os
from pathlib import Path

from app.auth.crypto_certs import (
    InvalidCertificateFile,
    cert_matches_serial,
    load_bundle,
    sign_challenge,
    verify_challenge,
)
from app.db.repositories.users import User


GENERIC_FAILURE_MESSAGE = (
    "No se pudo confirmar el certificado. Verifique el archivo .pfx y la contraseña."
)


def verify_certificate_file(user: User, pfx_path: Path, password: str) -> tuple[bool, str]:
    """Verifica que `pfx_path` (+ `password`) es el certificado vigente de `user`.

    Devuelve (ok, mensaje_de_error). Si ok es True, el mensaje va vacío.

    El mensaje de error es SIEMPRE el mismo genérico, sin importar la causa real
    (contraseña incorrecta, archivo dañado, o un certificado válido pero de OTRA
    cuenta) -- distinguir esos casos le dejaría saber a quien prueba un .pfx
    ajeno si acertó la contraseña de ese archivo, aunque no le sirva para entrar
    a esta cuenta."""
    try:
        pfx_bytes = pfx_path.read_bytes()
        private_key, certificate = load_bundle(pfx_bytes, password)
    except (InvalidCertificateFile, OSError):
        return False, GENERIC_FAILURE_MESSAGE

    if not cert_matches_serial(certificate, user.cert_serial or ""):
        return False, GENERIC_FAILURE_MESSAGE

    challenge = os.urandom(32)
    signature = sign_challenge(private_key, challenge)
    if not verify_challenge(user.cert_public_pem, challenge, signature):
        return False, GENERIC_FAILURE_MESSAGE

    return True, ""
