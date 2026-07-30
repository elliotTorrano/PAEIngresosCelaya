"""Datos de cuenta simplificados para Agente del PAE y Abogado: pueden ver
su usuario y nombre completo, y actualizar únicamente su correo. Sin
confirmación por certificado (a diferencia de AccountSettingsView), porque
el correo no forma parte de lo firmado en el certificado."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.db.repositories import users as users_repo


class SimpleAccountView(QWidget):
    def __init__(self, user: users_repo.User, parent=None):
        super().__init__(parent)
        self.user = user

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Usuario: {user.username}"))
        layout.addWidget(QLabel(f"Nombre completo: {user.full_name}"))

        layout.addWidget(QLabel("Correo electrónico:"))
        self.email_input = QLineEdit(user.email or "")
        layout.addWidget(self.email_input)

        save_btn = QPushButton("Guardar correo")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _on_save(self) -> None:
        new_email = self.email_input.text().strip()
        if not new_email:
            QMessageBox.warning(self, "Correo vacío", "Ingresa un correo electrónico.")
            return

        users_repo.update_email(self.user.id, new_email)
        self.user.email = new_email
        QMessageBox.information(self, "Correo actualizado", "Tu correo electrónico se actualizó correctamente.")
