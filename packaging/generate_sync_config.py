"""Herramienta de DESARROLLO: genera resources/sync_config.enc (URL de la
base de Turso + token de SOLO LECTURA) a partir de datos capturados por
consola. No se empaqueta ejecutándose -- se corre una sola vez (o cuando se
rote el token de solo lectura) antes de compilar la versión que se va a
distribuir. El token de ESCRITURA nunca va aquí -- ver
app/ui/admin/sync_settings_view.py, donde lo pega el Administrador a mano
en su propia instalación.

Uso:
    python packaging/generate_sync_config.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sync.config import _SYNC_CONFIG_KEY  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[1] / "resources" / "sync_config.enc"


def main() -> None:
    database_url = input("URL de la base (libsql://... o https://...): ").strip()
    read_only_token = input("Token de SOLO LECTURA (turso db tokens create ... --read-only): ").strip()

    data = {"database_url": database_url, "read_only_token": read_only_token}

    ciphertext = Fernet(_SYNC_CONFIG_KEY).encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    OUTPUT.write_bytes(ciphertext)
    print(f"Escrito: {OUTPUT}")


if __name__ == "__main__":
    main()
