from unittest.mock import patch

from app.auth.enrollment import enroll_certificate
from app.auth.recovery_codes import verify_recovery_code
from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_AGENTE_PAE, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo


def test_enroll_certificate_generates_recovery_code_for_administrador(db, tmp_path):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    recovery_code = enroll_certificate(admin, password="clave-segura", save_path=tmp_path / "admin.pfx")

    assert recovery_code is not None
    refreshed = users_repo.get_by_id(admin.id)
    assert users_repo.has_certificate(refreshed)
    assert verify_recovery_code(refreshed, recovery_code) is True


def test_enroll_certificate_generates_recovery_code_for_superusuario(db, tmp_path):
    su = users_repo.create_user(
        username="super1", role=ROLE_SUPERUSUARIO, full_name="Super", email="s@s.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    recovery_code = enroll_certificate(su, password="clave-segura", save_path=tmp_path / "super1.pfx")

    assert recovery_code is not None
    refreshed = users_repo.get_by_id(su.id)
    assert verify_recovery_code(refreshed, recovery_code) is True


def test_enroll_certificate_no_recovery_code_for_agente(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    recovery_code = enroll_certificate(agente, password="clave-segura", save_path=tmp_path / "agente1.pfx")

    assert recovery_code is None
    refreshed = users_repo.get_by_id(agente.id)
    assert refreshed.recovery_code_hash is None


def test_enroll_certificate_records_file_path(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    save_path = tmp_path / "agente1.pfx"

    enroll_certificate(agente, password="clave-segura", save_path=save_path)

    refreshed = users_repo.get_by_id(agente.id)
    assert refreshed.cert_file_path == str(save_path)


def test_reenroll_deletes_previous_certificate_file(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    first_path = tmp_path / "agente1_old.pfx"
    enroll_certificate(agente, password="clave-1", save_path=first_path)
    assert first_path.exists()

    refreshed = users_repo.get_by_id(agente.id)
    second_path = tmp_path / "agente1_new.pfx"
    enroll_certificate(refreshed, password="clave-2", save_path=second_path)

    assert not first_path.exists()
    assert second_path.exists()


def test_reenroll_same_path_does_not_delete_new_file(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    same_path = tmp_path / "agente1.pfx"
    enroll_certificate(agente, password="clave-1", save_path=same_path)

    refreshed = users_repo.get_by_id(agente.id)
    enroll_certificate(refreshed, password="clave-2", save_path=same_path)

    assert same_path.exists()


def test_reenroll_missing_previous_file_does_not_raise(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    first_path = tmp_path / "agente1_old.pfx"
    enroll_certificate(agente, password="clave-1", save_path=first_path)
    first_path.unlink()  # se movió o se borró manualmente antes de reenrolar

    refreshed = users_repo.get_by_id(agente.id)
    second_path = tmp_path / "agente1_new.pfx"
    enroll_certificate(refreshed, password="clave-2", save_path=second_path)

    assert second_path.exists()


def test_enroll_certificate_pushes_updated_user_to_remote_directory(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    with patch("app.auth.enrollment.user_directory.push_user") as mock_push:
        enroll_certificate(agente, password="clave-segura", save_path=tmp_path / "agente1.pfx")

    mock_push.assert_called_once()
    pushed_user = mock_push.call_args[0][0]
    assert pushed_user.username == "agente1"
    assert pushed_user.cert_public_pem is not None


def test_reenroll_rotates_recovery_code(db, tmp_path):
    admin = users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    first_code = enroll_certificate(admin, password="clave-1", save_path=tmp_path / "admin1.pfx")
    refreshed = users_repo.get_by_id(admin.id)

    second_code = enroll_certificate(refreshed, password="clave-2", save_path=tmp_path / "admin2.pfx")
    refreshed2 = users_repo.get_by_id(admin.id)

    assert first_code != second_code
    assert verify_recovery_code(refreshed2, first_code) is False
    assert verify_recovery_code(refreshed2, second_code) is True
