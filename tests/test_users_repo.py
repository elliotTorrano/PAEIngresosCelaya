from app.config import AUTH_TYPE_PASSWORD, ROLE_ABOGADO
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
