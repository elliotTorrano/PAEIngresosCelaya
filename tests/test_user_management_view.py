from PySide6.QtWidgets import QGroupBox, QLineEdit, QTableWidget

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo
from app.ui.admin.user_management_view import UserManagementView


def _make_admin():
    return users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin Uno", email="admin@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_super():
    return users_repo.create_user(
        username="super1", role=ROLE_SUPERUSUARIO, full_name="Super Uno", email="s@s.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _find_admin_box(view) -> QGroupBox:
    return next(b for b in view.findChildren(QGroupBox) if b.title() == "Administrador")


def test_super_sees_administrador_box_with_current_admin(qapp, db):
    admin = _make_admin()
    su = _make_super()

    view = UserManagementView(su)
    admin_table = _find_admin_box(view).findChild(QTableWidget)

    assert admin_table.rowCount() == 1
    assert admin_table.item(0, 0).text() == admin.username
    assert admin_table.item(0, 1).text() == admin.full_name
    assert admin_table.item(0, 2).text() == admin.email
    assert admin_table.item(0, 3).text() == "Sí"


def test_administrador_box_has_no_add_form(qapp, db):
    _make_admin()
    su = _make_super()
    view = UserManagementView(su)

    assert _find_admin_box(view).findChild(QLineEdit) is None


def test_no_administrador_configured_shows_empty_table(qapp, db):
    su = _make_super()
    view = UserManagementView(su)

    admin_table = _find_admin_box(view).findChild(QTableWidget)
    assert admin_table.rowCount() == 0


def test_administrador_sees_own_data_in_usuarios(qapp, db):
    admin = _make_admin()
    view = UserManagementView(admin)

    admin_table = _find_admin_box(view).findChild(QTableWidget)
    assert admin_table.rowCount() == 1
    assert admin_table.item(0, 0).text() == admin.username
