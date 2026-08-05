"""Alta y consulta de cuentas de Agentes del PAE y Abogados, y consulta (sólo
lectura) de la cuenta única del Administrador -- se sigue sembrando
automáticamente, no se da de alta desde aquí; sus datos de identidad y
certificado se cambian desde 'Datos de cuenta'."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.passwords import hash_password
from app.config import (
    AUTH_TYPE_CERTIFICADO,
    AUTH_TYPE_PASSWORD,
    ROLE_ABOGADO,
    ROLE_AGENTE_PAE,
    ROLE_REPORTEADOR,
)
from app.db.repositories import users as users_repo
from app.sync import user_directory


class UserManagementView(QWidget):
    def __init__(self, admin_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.admin_user = admin_user

        outer_layout = QVBoxLayout(self)

        boxes_layout = QHBoxLayout()
        boxes_layout.addWidget(self._build_administrador_box())
        boxes_layout.addWidget(self._build_role_box("Agentes del PAE", ROLE_AGENTE_PAE, with_password=False))
        boxes_layout.addWidget(self._build_role_box("Abogados", ROLE_ABOGADO, with_password=True))
        boxes_layout.addWidget(self._build_role_box("Reporteadores", ROLE_REPORTEADOR, with_password=False))
        outer_layout.addLayout(boxes_layout)

        sync_btn = QPushButton("Sincronizar ahora")
        sync_btn.setToolTip(
            "Sube al directorio remoto todas las cuentas de Agente/Abogado/"
            "Reporteador -- sirve para reintentar si algún alta falló por falta "
            "de conexión, o para las cuentas creadas antes de esta función."
        )
        sync_btn.clicked.connect(self._on_sync_now)
        outer_layout.addWidget(sync_btn)

    def _on_sync_now(self) -> None:
        for role in (ROLE_AGENTE_PAE, ROLE_ABOGADO, ROLE_REPORTEADOR):
            for u in users_repo.list_by_role(role, active_only=False):
                user_directory.push_user(u)
        QMessageBox.information(
            self, "Sincronización",
            "Se intentó subir todas las cuentas al directorio remoto. Si no hay "
            "conexión o el token de escritura no está configurado, no pasa nada -- "
            "se puede volver a intentar en cualquier momento.",
        )

    def _build_administrador_box(self) -> QGroupBox:
        box = QGroupBox("Administrador")
        layout = QVBoxLayout(box)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Usuario", "Nombre", "Correo", "Activo"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        layout.addWidget(
            QLabel(
                "Es una cuenta única: no se da de alta desde aquí. Sus datos de "
                "identidad y certificado se cambian desde 'Datos de cuenta'."
            )
        )

        admin = users_repo.get_administrator()
        if admin is not None:
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem(admin.username))
            table.setItem(0, 1, QTableWidgetItem(admin.full_name))
            table.setItem(0, 2, QTableWidgetItem(admin.email or ""))
            table.setItem(0, 3, QTableWidgetItem("Sí" if admin.active else "No"))

        return box

    def _build_role_box(self, title: str, role: str, *, with_password: bool) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Usuario", "Nombre", "Correo", "Activo"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        username_input = QLineEdit()
        username_input.setPlaceholderText("Usuario")
        fullname_input = QLineEdit()
        fullname_input.setPlaceholderText("Nombre completo")
        email_input = QLineEdit()
        email_input.setPlaceholderText("Correo electrónico")
        layout.addWidget(username_input)
        layout.addWidget(fullname_input)
        layout.addWidget(email_input)

        password_input = None
        if with_password:
            password_input = QLineEdit()
            password_input.setPlaceholderText("Contraseña inicial")
            password_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(password_input)
        else:
            layout.addWidget(QLabel("El certificado se genera en su primer inicio de sesión."))

        add_btn = QPushButton(f"Agregar")
        layout.addWidget(add_btn)

        def refresh() -> None:
            table.setRowCount(0)
            for u in users_repo.list_by_role(role, active_only=False):
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(u.username))
                table.setItem(row, 1, QTableWidgetItem(u.full_name))
                table.setItem(row, 2, QTableWidgetItem(u.email or ""))
                table.setItem(row, 3, QTableWidgetItem("Sí" if u.active else "No"))

        def on_add() -> None:
            username = username_input.text().strip()
            full_name = fullname_input.text().strip()
            email = email_input.text().strip()
            if not username or not full_name:
                QMessageBox.warning(self, "Datos incompletos", "Usuario y nombre completo son obligatorios.")
                return
            if users_repo.get_by_username(username) is not None:
                QMessageBox.warning(self, "Usuario existente", f"Ya existe un usuario '{username}'.")
                return

            if with_password:
                password = password_input.text()
                if len(password) < 6:
                    QMessageBox.warning(self, "Contraseña inválida", "La contraseña debe tener al menos 6 caracteres.")
                    return
                pwd_hash, salt = hash_password(password)
                new_user = users_repo.create_user(
                    username=username, role=role, full_name=full_name, email=email,
                    auth_type=AUTH_TYPE_PASSWORD, password_hash=pwd_hash, password_salt=salt,
                    must_change_password=True,
                )
                password_input.clear()
            else:
                new_user = users_repo.create_user(
                    username=username, role=role, full_name=full_name, email=email,
                    auth_type=AUTH_TYPE_CERTIFICADO,
                )

            user_directory.push_user(new_user)
            username_input.clear()
            fullname_input.clear()
            email_input.clear()
            refresh()

        add_btn.clicked.connect(on_add)
        refresh()
        return box
