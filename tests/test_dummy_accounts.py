from app.auth.dummy_accounts import ensure_dummy_accounts
from app.auth.passwords import verify_password
from app.config import (
    AUTH_TYPE_PASSWORD,
    DUMMY_ABOGADO_USERNAME,
    DUMMY_AGENTE_USERNAME,
    DUMMY_PASSWORD,
    ROLE_ABOGADO,
    ROLE_AGENTE_PAE,
    is_dummy_user,
)
from app.db.repositories import users as users_repo


def test_ensure_dummy_accounts_creates_both_users(db):
    ensure_dummy_accounts()

    agente = users_repo.get_by_username(DUMMY_AGENTE_USERNAME)
    abogado = users_repo.get_by_username(DUMMY_ABOGADO_USERNAME)

    assert agente is not None
    assert agente.role == ROLE_AGENTE_PAE
    assert agente.auth_type == AUTH_TYPE_PASSWORD
    assert verify_password(DUMMY_PASSWORD, agente.password_hash, agente.password_salt)

    assert abogado is not None
    assert abogado.role == ROLE_ABOGADO
    assert abogado.auth_type == AUTH_TYPE_PASSWORD
    assert verify_password(DUMMY_PASSWORD, abogado.password_hash, abogado.password_salt)


def test_ensure_dummy_accounts_is_idempotent(db):
    ensure_dummy_accounts()
    first_agente_id = users_repo.get_by_username(DUMMY_AGENTE_USERNAME).id

    ensure_dummy_accounts()

    assert users_repo.get_by_username(DUMMY_AGENTE_USERNAME).id == first_agente_id
    assert users_repo.count_by_role(ROLE_AGENTE_PAE) == 1
    assert users_repo.count_by_role(ROLE_ABOGADO) == 1


def test_is_dummy_user(db):
    ensure_dummy_accounts()
    agente = users_repo.get_by_username(DUMMY_AGENTE_USERNAME)
    abogado = users_repo.get_by_username(DUMMY_ABOGADO_USERNAME)
    real_agente = users_repo.create_user(
        username="agente_real", role=ROLE_AGENTE_PAE, full_name="Real", email=None,
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    assert is_dummy_user(agente)
    assert is_dummy_user(abogado)
    assert not is_dummy_user(real_agente)
