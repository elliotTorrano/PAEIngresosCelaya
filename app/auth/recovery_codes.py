"""Código de respaldo local para Súper-usuario/Administrador.

Son las dos únicas cuentas del sistema para las que no hay garantía de que
"alguien más" esté disponible para aprobar una solicitud de recuperación (el
Administrador es único, y el Súper-usuario no tiene a nadie por encima). Por
eso, además del flujo mediado por archivos de app/auth/recovery.py, cada una
recibe -- al generar su certificado, ya sea la primera vez o al reenrolar
después de perderlo -- un código de respaldo que se muestra una sola vez y
que permite recuperar el acceso de inmediato en la misma máquina, sin
depender de ningún otro usuario.

Sólo se guarda el hash (mismo esquema PBKDF2 que las contraseñas); el código
en texto plano nunca se persiste. Cada vez que se emite un certificado nuevo
se sobreescribe el código anterior, así que sólo el más reciente es válido.
"""

from __future__ import annotations

import secrets

from app.auth.passwords import hash_password, verify_password
from app.config import ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories.users import User

ROLES_WITH_RECOVERY_CODE = (ROLE_SUPERUSUARIO, ROLE_ADMINISTRADOR)

# Sin O/0, I/1/L: se pensó para transcribirse a mano desde una copia impresa.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_GROUP_COUNT = 4
_GROUP_SIZE = 4


def generate_recovery_code() -> str:
    groups = ["".join(secrets.choice(_ALPHABET) for _ in range(_GROUP_SIZE)) for _ in range(_GROUP_COUNT)]
    return "-".join(groups)


def hash_recovery_code(code: str) -> tuple[str, str]:
    return hash_password(_normalize(code))


def verify_recovery_code(user: User, code: str) -> bool:
    if not user.recovery_code_hash or not user.recovery_code_salt:
        return False
    return verify_password(_normalize(code), user.recovery_code_hash, user.recovery_code_salt)


def _normalize(code: str) -> str:
    return code.strip().upper()
