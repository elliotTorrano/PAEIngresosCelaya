"""Ventana de inicio de sesión: usuario/contraseña (Abogado) o certificado (los demás roles)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.auth import session
from app.auth.cert_auth import verify_certificate_file
from app.auth.passwords import verify_password
from app.config import APP_NAME, AUTH_TYPE_CERTIFICADO
from app.db.repositories import users as users_repo
from app.ui.login.change_password_dialog import ChangePasswordDialog
from app.ui.login.enrollment_dialog import EnrollmentDialog
from app.ui.login.forgot_password_dialog import ForgotPasswordDialog
from app.ui.login.import_update_dialog import ImportUpdateDialog


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Iniciar sesión — {APP_NAME}")
        self.setMinimumWidth(420)
        self._user: users_repo.User | None = None
        self._cert_path: str | None = None

        outer = QVBoxLayout(self)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_username_page())
        self.stack.addWidget(self._build_password_page())
        self.stack.addWidget(self._build_cert_page())

        links = QHBoxLayout()
        forgot_link = QPushButton("Olvidé mi contraseña o certificado")
        forgot_link.setFlat(True)
        forgot_link.clicked.connect(self._on_forgot_password)
        import_link = QPushButton("Importar actualización del administrador")
        import_link.setFlat(True)
        import_link.clicked.connect(self._on_import_update)
        links.addWidget(forgot_link)
        links.addWidget(import_link)
        outer.addLayout(links)

    # --- Página 1: usuario -----------------------------------------------------
    def _build_username_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Usuario:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        continue_btn = QPushButton("Continuar")
        continue_btn.setDefault(True)
        continue_btn.setAutoDefault(True)
        continue_btn.clicked.connect(self._on_continue)
        layout.addWidget(continue_btn)

        self.username_input.returnPressed.connect(self._on_continue)
        return page

    def _on_continue(self) -> None:
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Falta información", "Escriba su usuario.")
            return

        user = users_repo.get_by_username(username)
        if user is None or not user.active:
            QMessageBox.warning(self, "Usuario no encontrado", "Usuario inválido o inactivo en esta instalación.")
            return

        self._user = user
        if user.auth_type == AUTH_TYPE_CERTIFICADO:
            if not users_repo.has_certificate(user):
                self._run_enrollment(user)
            else:
                self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(1)

    # --- Página 2: usuario + contraseña (Abogado) -------------------------------
    def _build_password_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Contraseña:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        login_btn = QPushButton("Iniciar sesión")
        login_btn.setDefault(True)
        login_btn.setAutoDefault(True)
        login_btn.clicked.connect(self._on_login_password)
        layout.addWidget(login_btn)

        self.password_input.returnPressed.connect(self._on_login_password)
        return page

    def _on_login_password(self) -> None:
        user = self._user
        password = self.password_input.text()
        if not user.password_hash or not verify_password(password, user.password_hash, user.password_salt):
            QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña no es válida.")
            return

        if user.must_change_password:
            change_dialog = ChangePasswordDialog(user, parent=self)
            if change_dialog.exec() != QDialog.DialogCode.Accepted:
                self.stack.setCurrentIndex(0)
                return
            user = users_repo.get_by_id(user.id)

        self._finish_login(user)

    # --- Página 3: certificado (Súper-usuario/Administrador/Agente) ------------
    def _build_cert_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Archivo de certificado (.pfx):"))
        cert_row = QHBoxLayout()
        self.cert_path_label = QLabel("(ninguno seleccionado)")
        browse_btn = QPushButton("Examinar...")
        browse_btn.clicked.connect(self._on_browse_cert)
        cert_row.addWidget(self.cert_path_label)
        cert_row.addWidget(browse_btn)
        layout.addLayout(cert_row)

        layout.addWidget(QLabel("Contraseña del certificado:"))
        self.cert_password_input = QLineEdit()
        self.cert_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.cert_password_input)

        login_btn = QPushButton("Iniciar sesión")
        login_btn.setDefault(True)
        login_btn.setAutoDefault(True)
        login_btn.clicked.connect(self._on_login_cert)
        layout.addWidget(login_btn)

        self.cert_password_input.returnPressed.connect(self._on_login_cert)
        return page

    def _on_browse_cert(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar certificado", "", "Certificado (*.pfx)")
        if file_path:
            self._cert_path = file_path
            self.cert_path_label.setText(file_path)

    def _on_login_cert(self) -> None:
        user = self._user
        if not self._cert_path:
            QMessageBox.warning(self, "Falta el certificado", "Seleccione su archivo .pfx.")
            return

        password = self.cert_password_input.text()
        ok, message = verify_certificate_file(user, Path(self._cert_path), password)
        if not ok:
            QMessageBox.warning(self, "No se pudo iniciar sesión", message)
            return

        self._finish_login(user)

    # --- Enrolamiento (primer login de un usuario de certificado) --------------
    def _run_enrollment(self, user: users_repo.User) -> None:
        dialog = EnrollmentDialog(user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._finish_login(users_repo.get_by_id(user.id))
        else:
            self.stack.setCurrentIndex(0)

    # --- Enlaces -----------------------------------------------------------------
    def _on_forgot_password(self) -> None:
        dialog = ForgotPasswordDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Especificación: tras generar la solicitud, el programa se cierra.
            self.reject()
            os._exit(0)

    def _on_import_update(self) -> None:
        ImportUpdateDialog(parent=self).exec()

    def _finish_login(self, user: users_repo.User) -> None:
        session.start(user)
        self.accept()

    @property
    def logged_in_user(self) -> users_repo.User | None:
        return session.current()
