import pytest

from app.auth.seed_crypto import decrypt_seed, encrypt_seed


def test_encrypt_decrypt_roundtrip():
    plaintext = b'{"hola": "mundo"}'
    ciphertext = encrypt_seed(plaintext)
    assert ciphertext != plaintext
    assert decrypt_seed(ciphertext) == plaintext


def test_decrypt_rejects_tampered_ciphertext():
    ciphertext = bytearray(encrypt_seed(b"datos"))
    ciphertext[-1] ^= 0xFF
    with pytest.raises(ValueError):
        decrypt_seed(bytes(ciphertext))


def test_decrypt_rejects_garbage():
    with pytest.raises(ValueError):
        decrypt_seed(b"no-es-un-token-fernet-valido")
