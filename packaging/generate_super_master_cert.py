"""Genera el certificado "maestro" del súper-usuario: el mismo certificado
que el programa reconocerá desde el primer arranque en CUALQUIER instalación
nueva, sin pedir enrolamiento.

IMPORTANTE -- corre este script en TU PROPIA terminal, nunca le pidas a un
asistente de IA que lo ejecute por ti: la contraseña que escribas aquí no
debe salir de tu computadora.

Qué hace:
1. Genera un par de llaves + certificado autofirmado (igual que el programa
   genera para cualquier usuario), protegido con la contraseña que elijas.
2. Guarda el archivo .pfx (la llave PRIVADA) donde tú indiques -- guárdalo en
   un lugar seguro (ej. una USB); es lo único que después necesitas llevar a
   cada máquina para iniciar sesión como súper-usuario.
3. Agrega la parte PÚBLICA de ese certificado a resources/seed_accounts.enc
   (que ya debe existir -- corre primero packaging/generate_seed.py), junto
   al usuario/nombre/correo del súper-usuario que ya tenía sembrados.

Cambio de modelo de seguridad a tener en cuenta: como el mismo certificado
queda reconocido en todas las instalaciones, si ese .pfx (o su contraseña)
se filtra alguna vez, cualquiera que lo tenga obtiene acceso de súper-usuario
en TODAS las instalaciones a la vez -- no sólo en una máquina, como pasaba
antes con un certificado independiente por máquina.

Si el súper-usuario YA tiene una instalación viva en alguna máquina con un
certificado distinto (generado antes de correr este script), ese certificado
deja de coincidir con el nuevo "maestro" -- hay que reenrolar en esa máquina
(con este mismo .pfx nuevo) la próxima vez que se inicie sesión ahí, o usar
ahí "Generar nuevo certificado" desde Datos de cuenta.

Uso:
    python packaging/generate_super_master_cert.py
"""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.crypto_certs import generate_certificate_bundle  # noqa: E402
from app.auth.seed_crypto import decrypt_seed, encrypt_seed  # noqa: E402

SEED_PATH = Path(__file__).resolve().parents[1] / "resources" / "seed_accounts.enc"


def _load_existing_seed() -> dict:
    if not SEED_PATH.exists():
        raise SystemExit(
            f"No se encontró {SEED_PATH}. Corre primero packaging/generate_seed.py "
            "para crear los datos base de súper-usuario/administrador."
        )
    return json.loads(decrypt_seed(SEED_PATH.read_bytes()).decode("utf-8"))


def main() -> None:
    seed = _load_existing_seed()
    su = seed.get("superusuario")
    if not su:
        raise SystemExit("resources/seed_accounts.enc no tiene datos de 'superusuario' todavía.")

    print(f"Generando certificado maestro para: {su['username']} ({su['full_name']})")
    print()

    password = getpass.getpass("Contraseña para proteger el certificado (mínimo 6 caracteres): ")
    confirm = getpass.getpass("Confirmar contraseña: ")
    if len(password) < 6:
        raise SystemExit("La contraseña debe tener al menos 6 caracteres.")
    if password != confirm:
        raise SystemExit("Las contraseñas no coinciden.")

    save_dir = input("Carpeta donde guardar el certificado (.pfx) [carpeta actual]: ").strip() or "."
    save_path = Path(save_dir) / f"{su['username']}_maestro.pfx"

    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=su["username"], full_name=su["full_name"], password=password
    )
    save_path.write_bytes(pfx_bytes)

    su["cert_public_pem"] = cert_public_pem
    su["cert_serial"] = cert_serial
    seed["superusuario"] = su

    ciphertext = encrypt_seed(json.dumps(seed, ensure_ascii=False).encode("utf-8"))
    SEED_PATH.write_bytes(ciphertext)

    print()
    print(f"Certificado maestro guardado en: {save_path.resolve()}")
    print(f"Actualizado: {SEED_PATH}")
    print()
    print(
        "Guarda ese .pfx en un lugar seguro (ej. una USB) junto con la contraseña "
        "que elegiste -- son lo único que necesitas llevar a cualquier máquina "
        "nueva para iniciar sesión como súper-usuario desde el primer arranque. "
        "Falta compilar el .exe de nuevo para que el seed_accounts.enc "
        "actualizado quede empacado (ver PUBLICAR_NUEVA_VERSION.md)."
    )


if __name__ == "__main__":
    main()
