from app.config import AUTH_TYPE_CERTIFICADO, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.ui.login.enrollment_dialog import EnrollmentDialog


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="ag@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_defer_button_sets_deferred_and_rejects(qapp, db):
    agente = _make_agente()
    dialog = EnrollmentDialog(agente)

    dialog._on_defer()

    assert dialog.deferred is True
    assert dialog.result() == 0  # QDialog.DialogCode.Rejected
    assert not users_repo.has_certificate(users_repo.get_by_id(agente.id))


def test_dialog_starts_not_deferred(qapp, db):
    agente = _make_agente()
    dialog = EnrollmentDialog(agente)
    assert dialog.deferred is False
