import pytest

from app.auth import first_run
from app.config import ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo


def _write_seed(tmp_path):
    seed_path = tmp_path / "seed_accounts.json"
    seed_path.write_text(
        '{"superusuario": {"username": "su1", "full_name": "Super Uno", "email": "su1@example.com"},'
        ' "administrador": {"username": "admin1", "full_name": "Admin Uno", "email": "admin1@example.com"}}',
        encoding="utf-8",
    )
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


def test_ensure_seed_accounts_missing_file_raises(db, monkeypatch, tmp_path):
    monkeypatch.setattr(first_run, "resource_dir", lambda: tmp_path)
    with pytest.raises(first_run.SeedFileMissingError):
        first_run.ensure_seed_accounts()
