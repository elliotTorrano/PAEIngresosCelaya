"""Alta automática y determinista del súper-usuario y el Administrador únicos.

Estas cuentas ya no se piden de forma interactiva: se siembran (si no existen
todavía en esta base de datos local) a partir de resources/seed_accounts.enc
-- un archivo cifrado que se empaqueta junto con el programa (ver
app/auth/seed_crypto.py y packaging/generate_seed.py). Así, sin importar en
qué máquina o cuántas veces se ejecute el .exe, siempre se crea exactamente
la misma cuenta de súper-usuario y de Administrador -- nunca se vuelve a
preguntar, y el nombre/correo reales no quedan en texto plano dentro del .exe.

Si el seed también trae `cert_public_pem`/`cert_serial` para el súper-usuario
(generados una sola vez con packaging/generate_super_master_cert.py), esa
cuenta queda con el certificado "maestro" ya registrado desde el primer
arranque en CUALQUIER máquina -- el súper-usuario inicia sesión ahí con el
mismo archivo .pfx de siempre, sin pasar por el enrolamiento. El Administrador
nunca se siembra con certificado: sigue generando el suyo, propio de cada
máquina, en su primer inicio de sesión."""

from __future__ import annotations

import json

from app.auth.seed_crypto import decrypt_seed
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo
from app.utils.paths import resource_dir

SEED_FILE_NAME = "seed_accounts.enc"


class SeedFileMissingError(Exception):
    """resources/seed_accounts.enc no está presente o es inválido."""


def _load_seed() -> dict:
    path = resource_dir() / SEED_FILE_NAME
    if not path.exists():
        raise SeedFileMissingError(f"No se encontró {path}. El programa no puede crear sus cuentas base.")
    try:
        plaintext = decrypt_seed(path.read_bytes())
        return json.loads(plaintext.decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SeedFileMissingError(f"No se pudo leer {path}: {exc}") from exc


def ensure_seed_accounts() -> None:
    """Crea el súper-usuario y el Administrador únicos si todavía no existen
    localmente. Idempotente: en instalaciones ya sembradas no hace nada."""
    if users_repo.count_by_role(ROLE_SUPERUSUARIO) > 0 and users_repo.count_by_role(ROLE_ADMINISTRADOR) > 0:
        return

    seed = _load_seed()

    if users_repo.count_by_role(ROLE_SUPERUSUARIO) == 0:
        su = seed["superusuario"]
        user = users_repo.create_user(
            username=su["username"], role=ROLE_SUPERUSUARIO, full_name=su["full_name"],
            email=su["email"], auth_type=AUTH_TYPE_CERTIFICADO,
        )
        cert_public_pem = su.get("cert_public_pem")
        cert_serial = su.get("cert_serial")
        if cert_public_pem and cert_serial:
            users_repo.set_certificate(user.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)

    if users_repo.count_by_role(ROLE_ADMINISTRADOR) == 0:
        admin = seed["administrador"]
        users_repo.create_user(
            username=admin["username"], role=ROLE_ADMINISTRADOR, full_name=admin["full_name"],
            email=admin["email"], auth_type=AUTH_TYPE_CERTIFICADO,
        )
