from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_ADMINISTRADOR
from app.db.repositories import users as users_repo


def test_create_user_with_must_change_password(db):
    user = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="a@a.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y", must_change_password=True,
    )
    assert user.must_change_password is True

    users_repo.set_password(user.id, password_hash="new", password_salt="salt", must_change_password=False)
    refreshed = users_repo.get_by_id(user.id)
    assert refreshed.must_change_password is False
    assert refreshed.password_hash == "new"


def test_create_user_defaults_to_no_forced_change(db):
    user = users_repo.create_user(
        username="abogado2", role=ROLE_ABOGADO, full_name="Abogado Dos", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    assert user.must_change_password is False


def test_update_identity_and_clear_certificate(db):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Administrador", email="admin@example.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    users_repo.set_certificate(admin.id, cert_public_pem="PEM-FALSO", cert_serial="abc123")
    assert users_repo.has_certificate(users_repo.get_by_id(admin.id))

    users_repo.update_identity(admin.id, username="admin2", full_name="Administrador Nuevo", email="nuevo@example.com")
    users_repo.clear_certificate(admin.id)

    refreshed = users_repo.get_by_id(admin.id)
    assert refreshed.username == "admin2"
    assert refreshed.full_name == "Administrador Nuevo"
    assert refreshed.email == "nuevo@example.com"
    assert not users_repo.has_certificate(refreshed)


def test_update_email_only_changes_email(db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_ADMINISTRADOR, full_name="Agente Uno", email="viejo@example.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    users_repo.update_email(agente.id, "nuevo@example.com")

    refreshed = users_repo.get_by_id(agente.id)
    assert refreshed.email == "nuevo@example.com"
    assert refreshed.username == "agente1"
    assert refreshed.full_name == "Agente Uno"
