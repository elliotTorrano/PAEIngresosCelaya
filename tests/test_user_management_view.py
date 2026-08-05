from unittest.mock import patch

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


def test_reporteadores_box_has_no_password_field_and_creates_cert_user(qapp, db):
    from app.config import ROLE_REPORTEADOR
    from app.db.repositories import users as users_repo_module

    su = _make_super()
    view = UserManagementView(su)
    box = next(b for b in view.findChildren(QGroupBox) if b.title() == "Reporteadores")

    # Igual que Agentes del PAE: sin campo de contraseña (se autentica con certificado).
    password_fields = [
        edit for edit in box.findChildren(QLineEdit)
        if edit.echoMode() == QLineEdit.EchoMode.Password
    ]
    assert password_fields == []

    inputs = box.findChildren(QLineEdit)
    username_input, fullname_input, email_input = inputs[0], inputs[1], inputs[2]
    username_input.setText("reporteador1")
    fullname_input.setText("Reporteador Uno")
    email_input.setText("r@r.com")

    from PySide6.QtWidgets import QPushButton
    add_btn = next(b for b in box.findChildren(QPushButton) if b.text() == "Agregar")
    add_btn.click()

    created = users_repo_module.get_by_username("reporteador1")
    assert created is not None
    assert created.role == ROLE_REPORTEADOR
    assert created.auth_type == AUTH_TYPE_CERTIFICADO


def test_add_user_pushes_to_remote_directory(qapp, db):
    from PySide6.QtWidgets import QPushButton

    su = _make_super()
    view = UserManagementView(su)
    box = next(b for b in view.findChildren(QGroupBox) if b.title() == "Agentes del PAE")

    inputs = box.findChildren(QLineEdit)
    inputs[0].setText("agente_nuevo")
    inputs[1].setText("Agente Nuevo")
    inputs[2].setText("a@a.com")

    add_btn = next(b for b in box.findChildren(QPushButton) if b.text() == "Agregar")
    with patch("app.ui.admin.user_management_view.user_directory.push_user") as mock_push:
        add_btn.click()

    mock_push.assert_called_once()
    pushed_user = mock_push.call_args[0][0]
    assert pushed_user.username == "agente_nuevo"


def test_sync_now_button_pushes_all_synced_roles(qapp, db):
    from app.config import ROLE_AGENTE_PAE, ROLE_REPORTEADOR
    from PySide6.QtWidgets import QPushButton

    users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    users_repo.create_user(
        username="reporteador1", role=ROLE_REPORTEADOR, full_name="Reporteador Uno", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    su = _make_super()
    view = UserManagementView(su)

    sync_btn = next(b for b in view.findChildren(QPushButton) if b.text() == "Sincronizar ahora")
    with patch("app.ui.admin.user_management_view.user_directory.push_user") as mock_push, patch(
        "app.ui.admin.user_management_view.QMessageBox.information"
    ):
        sync_btn.click()

    pushed_usernames = {call.args[0].username for call in mock_push.call_args_list}
    assert pushed_usernames == {"agente1", "reporteador1"}
