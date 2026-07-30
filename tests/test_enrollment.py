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
