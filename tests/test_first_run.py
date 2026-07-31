import json

import pytest

from app.auth import first_run
from app.auth.seed_crypto import encrypt_seed
from app.config import ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo


def _write_seed(tmp_path):
    seed_path = tmp_path / "seed_accounts.enc"
    data = {
        "superusuario": {"username": "su1", "full_name": "Super Uno", "email": "su1@example.com"},
        "administrador": {"username": "admin1", "full_name": "Admin Uno", "email": "admin1@example.com"},
    }
    seed_path.write_bytes(encrypt_seed(json.dumps(data).encode("utf-8")))
    return seed_path


def test_ensure_seed_accounts_creates_once(db, monkeypatch, tmp_path):
    _write_seed(tmp_path)
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)

    first_run.ensure_seed_accounts()
    assert users_repo.count_by_role(ROLE_SUPERUSUARIO) == 1
    assert users_repo.count_by_role(ROLE_ADMINISTRADOR) == 1

    su = users_repo.list_by_role(ROLE_SUPERUSUARIO, active_only=False)[0]
    admin = users_repo.list_by_role(ROLE_ADMINISTRADOR, active_only=False)[0]
    assert su.username == "su1"
    assert admin.username == "admin1"

    # Segunda "ejecución" del programa (misma base): no debe duplicar ni fallar.
    first_run.ensure_seed_accounts()
    assert users_repo.count_by_role(ROLE_SUPERUSUARIO) == 1
    assert users_repo.count_by_role(ROLE_ADMINISTRADOR) == 1


def test_ensure_seed_accounts_seeds_superusuario_certificate_when_present(db, monkeypatch, tmp_path):
    seed_path = tmp_path / "seed_accounts.enc"
    data = {
        "superusuario": {
            "username": "su1", "full_name": "Super Uno", "email": "su1@example.com",
            "cert_public_pem": "PEM-MAESTRO", "cert_serial": "abc123",
        },
        "administrador": {"username": "admin1", "full_name": "Admin Uno", "email": "admin1@example.com"},
    }
    seed_path.write_bytes(encrypt_seed(json.dumps(data).encode("utf-8")))
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)

    first_run.ensure_seed_accounts()

    su = users_repo.list_by_role(ROLE_SUPERUSUARIO, active_only=False)[0]
    assert users_repo.has_certificate(su)
    assert su.cert_public_pem == "PEM-MAESTRO"
    assert su.cert_serial == "abc123"

    admin = users_repo.list_by_role(ROLE_ADMINISTRADOR, active_only=False)[0]
    assert not users_repo.has_certificate(admin)


def test_ensure_seed_accounts_without_certificate_fields_still_requires_enrollment(db, monkeypatch, tmp_path):
    _write_seed(tmp_path)  # sin cert_public_pem/cert_serial, como antes
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)

    first_run.ensure_seed_accounts()

    su = users_repo.list_by_role(ROLE_SUPERUSUARIO, active_only=False)[0]
    assert not users_repo.has_certificate(su)


def test_ensure_seed_accounts_missing_file_raises(db, monkeypatch, tmp_path):
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)
    with pytest.raises(first_run.SeedFileMissingError):
        first_run.ensure_seed_accounts()


def test_ensure_seed_accounts_rejects_tampered_file(db, monkeypatch, tmp_path):
    seed_path = _write_seed(tmp_path)
    tampered = bytearray(seed_path.read_bytes())
    tampered[-1] ^= 0xFF
    seed_path.write_bytes(bytes(tampered))
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)

    with pytest.raises(first_run.SeedFileMissingError):
        first_run.ensure_seed_accounts()
