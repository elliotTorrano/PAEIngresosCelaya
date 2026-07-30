from app.auth.recovery_codes import (
    ROLES_WITH_RECOVERY_CODE,
    generate_recovery_code,
    hash_recovery_code,
    verify_recovery_code,
)
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories.users import User


def _make_user(recovery_code_hash=None, recovery_code_salt=None):
    return User(
        id=1, username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO, password_hash=None, password_salt=None,
        cert_public_pem=None, cert_serial=None,
        recovery_code_hash=recovery_code_hash, recovery_code_salt=recovery_code_salt,
        must_change_password=False, active=True,
    )


def test_roles_with_recovery_code():
    assert ROLE_SUPERUSUARIO in ROLES_WITH_RECOVERY_CODE
    assert ROLE_ADMINISTRADOR in ROLES_WITH_RECOVERY_CODE


def test_generate_recovery_code_format():
    code = generate_recovery_code()
    parts = code.split("-")
    assert len(parts) == 4
    assert all(len(p) == 4 for p in parts)


def test_generate_recovery_code_is_random():
    assert generate_recovery_code() != generate_recovery_code()


def test_verify_recovery_code_roundtrip():
    code = generate_recovery_code()
    code_hash, code_salt = hash_recovery_code(code)
    user = _make_user(code_hash, code_salt)
    assert verify_recovery_code(user, code) is True


def test_verify_recovery_code_ignores_case_and_surrounding_whitespace():
    code = generate_recovery_code()
    code_hash, code_salt = hash_recovery_code(code)
    user = _make_user(code_hash, code_salt)
    assert verify_recovery_code(user, f"  {code.lower()}  ") is True


def test_verify_recovery_code_wrong_code():
    code = generate_recovery_code()
    code_hash, code_salt = hash_recovery_code(code)
    user = _make_user(code_hash, code_salt)
    assert verify_recovery_code(user, "ZZZZ-ZZZZ-ZZZZ-ZZZZ") is False


def test_verify_recovery_code_no_code_stored():
    user = _make_user(None, None)
    assert verify_recovery_code(user, "ANY-CODE-VALUE-HERE") is False
