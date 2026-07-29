"""Herramienta de DESARROLLO: genera resources/seed_accounts.enc a partir de datos
capturados por consola. No se empaqueta en el .exe -- se corre una sola vez (o
cuando cambien los datos por defecto del súper-usuario/Administrador) antes de
compilar la versión que se va a distribuir.

Uso:
    python packaging/generate_seed.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.seed_crypto import encrypt_seed  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[1] / "resources" / "seed_accounts.enc"


def main() -> None:
    print("== Súper-usuario ==")
    su_username = input("Usuario: ").strip()
    su_full_name = input("Nombre completo: ").strip()
    su_email = input("Correo: ").strip()

    print("== Administrador ==")
    admin_username = input("Usuario: ").strip()
    admin_full_name = input("Nombre completo: ").strip()
    admin_email = input("Correo: ").strip()

    data = {
        "superusuario": {"username": su_username, "full_name": su_full_name, "email": su_email},
        "administrador": {"username": admin_username, "full_name": admin_full_name, "email": admin_email},
    }

    ciphertext = encrypt_seed(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    OUTPUT.write_bytes(ciphertext)
    print(f"Escrito: {OUTPUT}")


if __name__ == "__main__":
    main()
