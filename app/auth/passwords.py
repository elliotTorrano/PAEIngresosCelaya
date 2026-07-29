"""Hash/verificación de contraseñas simples (rol Abogado) con PBKDF2-HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac
import os

ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Devuelve (password_hash_hex, salt_hex)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    salt = bytes.fromhex(password_salt)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return hmac.compare_digest(digest.hex(), password_hash)
