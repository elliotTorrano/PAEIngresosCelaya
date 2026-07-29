from app.auth.passwords import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    password_hash, salt = hash_password("MiClaveSegura123")
    assert verify_password("MiClaveSegura123", password_hash, salt)


def test_verify_rejects_wrong_password():
    password_hash, salt = hash_password("MiClaveSegura123")
    assert not verify_password("otra-clave", password_hash, salt)


def test_different_salts_for_same_password():
    hash1, salt1 = hash_password("igual")
    hash2, salt2 = hash_password("igual")
    assert salt1 != salt2
    assert hash1 != hash2
