"""Cambio de contraseña obligatorio (Abogado): primer inicio de sesión o tras un reset del Administrador."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from app.auth.passwords import hash_password
from app.config import window_title
from app.db.repositories import users as users_repo


class ChangePasswordDialog(QDialog):
    def __init__(self, user: users_repo.User, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle(window_title("Cambio de contraseña obligatorio"))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Por seguridad, debe establecer una nueva contraseña antes de continuar."))

        layout.addWidget(QLabel("Nueva contraseña:"))
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_password_input)

        layout.addWidget(QLabel("Confirmar contraseña:"))
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_password_input)

        save_btn = QPushButton("Guardar y continuar")
        save_btn.setDefault(True)
        save_btn.setAutoDefault(True)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        self.new_password_input.returnPressed.connect(self._on_save)
        self.confirm_password_input.returnPressed.connect(self._on_save)

    def _on_save(self) -> None:
        password = self.new_password_input.text()
        confirm = self.confirm_password_input.text()

        if len(password) < 6:
            QMessageBox.warning(self, "Contraseña inválida", "La contraseña debe tener al menos 6 caracteres.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Contraseña inválida", "Las contraseñas no coinciden.")
            return

        pwd_hash, salt = hash_password(password)
        users_repo.set_password(self.user.id, password_hash=pwd_hash, password_salt=salt, must_change_password=False)
        self.accept()
