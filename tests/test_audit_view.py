from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories import users as users_repo
from app.ui.admin.audit_view import AuditView


def _make_admin():
    return users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Administrador", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_close_clears_displayed_data(qapp, db):
    view = AuditView(_make_admin())

    view.source_label.setText("Mostrando (sólo lectura): C:/algo/pae.db")
    view.files_table.insertRow(0)
    view.batches_table.insertRow(0)

    view._on_close()

    assert view.source_label.text() == "(ninguna base importada todavía)"
    assert view.files_table.rowCount() == 0
    assert view.batches_table.rowCount() == 0
