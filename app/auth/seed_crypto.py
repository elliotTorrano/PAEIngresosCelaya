"""Cifrado simétrico del archivo de sembrado (súper-usuario/administrador).

No es un secreto absoluto: la clave vive dentro del propio binario, así que
alguien dispuesto a decompilar el .exe podría eventualmente recuperarla. Lo
que sí evita es que, al abrir/extraer el .exe con un extractor común (7-Zip,
pyinstxtractor, etc.), quede a la vista en texto plano el nombre y correo
reales del súper-usuario y del Administrador.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

# Clave fija del proyecto para ofuscar resources/seed_accounts.enc.
# Si se rota, hay que volver a cifrar ese archivo con packaging/generate_seed.py.
_SEED_KEY = b"LAIehCTHgLUw9vC9ktxES3DM-O-ivETue7bebztVXRE="


def encrypt_seed(plaintext: bytes) -> bytes:
    return Fernet(_SEED_KEY).encrypt(plaintext)


def decrypt_seed(ciphertext: bytes) -> bytes:
    try:
        return Fernet(_SEED_KEY).decrypt(ciphertext)
    except InvalidToken as exc:
        raise ValueError("El archivo de sembrado está dañado o fue alterado.") from exc
