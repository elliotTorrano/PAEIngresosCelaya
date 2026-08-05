"""Config de conexión al directorio remoto de usuarios (Turso).

Igual que app/auth/seed_crypto.py con resources/seed_accounts.enc: la URL de
la base y el token de SOLO LECTURA (nunca el de escritura -- ese vive en
app_settings, ver app/db/repositories/settings.py, y lo pega el
Administrador a mano una sola vez) se hornean en el .exe como un recurso
cifrado con Fernet, para no dejarlos en texto plano al extraer el ejecutable
con un extractor común (7-Zip, pyinstxtractor, etc.). No es un secreto
absoluto -- la clave de cifrado vive en este mismo archivo -- pero el token
horneado es de solo lectura: lo peor que alguien podría hacer con él es leer
el directorio de cuentas, nunca escribirlo.

Mientras no exista resources/sync_config.enc (se genera con
packaging/generate_sync_config.py una vez haya credenciales reales de
Turso), o para desarrollo local, se pueden usar las variables de entorno
TURSO_DATABASE_URL y TURSO_READ_TOKEN en su lugar.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.utils.paths import resource_dir

# Clave fija del proyecto para ofuscar resources/sync_config.enc. Si se
# rota, hay que volver a cifrar ese archivo con packaging/generate_sync_config.py.
_SYNC_CONFIG_KEY = b"gjvFltpDLoyRQPSvtyfoR9IZdrx3SudfCWSm-E7x2WY="
_SYNC_CONFIG_FILENAME = "sync_config.enc"


@lru_cache(maxsize=1)
def _baked_config() -> dict | None:
    path = resource_dir() / _SYNC_CONFIG_FILENAME
    if not path.exists():
        return None
    try:
        plaintext = Fernet(_SYNC_CONFIG_KEY).decrypt(path.read_bytes())
        return json.loads(plaintext)
    except (InvalidToken, ValueError, OSError):
        return None


def database_url() -> str | None:
    env_value = os.environ.get("TURSO_DATABASE_URL")
    if env_value:
        return env_value
    config = _baked_config()
    return config.get("database_url") if config else None


def read_only_token() -> str | None:
    env_value = os.environ.get("TURSO_READ_TOKEN")
    if env_value:
        return env_value
    config = _baked_config()
    return config.get("read_only_token") if config else None
