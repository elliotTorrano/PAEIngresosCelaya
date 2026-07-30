"""Datos de cuenta simplificados para Agente del PAE y Abogado: pueden ver
su usuario y nombre completo, y actualizar su correo. Además, según cómo se
autentiquen, cada uno puede renovar su propia credencial sin depender de
nadie más: el Agente (certificado) puede generar uno nuevo, y el Abogado
(contraseña) puede cambiarla."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QGroupBox, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.auth.passwords import hash_password, verify_password
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD
from app.db.repositories import users as users_repo
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog


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

        if user.auth_type == AUTH_TYPE_CERTIFICADO:
            layout.addWidget(self._build_certificate_box())
        elif user.auth_type == AUTH_TYPE_PASSWORD:
            layout.addWidget(self._build_password_box())

        layout.addStretch()

    def _on_save(self) -> None:
        new_email = self.email_input.text().strip()
        if not new_email:
            QMessageBox.warning(self, "Correo vacío", "Ingresa un correo electrónico.")
            return

        users_repo.update_email(self.user.id, new_email)
        self.user.email = new_email
        QMessageBox.information(self, "Correo actualizado", "Tu correo electrónico se actualizó correctamente.")

    # --- Certificado (Agente del PAE) -------------------------------------------

    def _build_certificate_box(self) -> QGroupBox:
        box = QGroupBox("Certificado")
        layout = QVBoxLayout(box)
        layout.addWidget(
            QLabel(
                "Puedes generar un certificado nuevo cuando quieras (por ejemplo, para "
                "moverlo a otra USB). El certificado actual queda invalidado de inmediato; "
                "se te pedirá generar el nuevo en tu siguiente inicio de sesión."
            )
        )

        new_cert_btn = QPushButton("Generar nuevo certificado")
        new_cert_btn.clicked.connect(self._on_generate_new_certificate)
        layout.addWidget(new_cert_btn)
        return box

    def _on_generate_new_certificate(self) -> None:
        current = users_repo.get_by_id(self.user.id)
        if not users_repo.has_certificate(current):
            QMessageBox.warning(
                self,
                "Sin certificado registrado",
                "Todavía no tienes un certificado generado; debes iniciar sesión al menos "
                "una vez antes de poder generar uno nuevo.",
            )
            return

        confirm_dialog = CertificateConfirmDialog(current, parent=self)
        if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        users_repo.clear_certificate(current.id)

        QMessageBox.information(
            self,
            "Certificado invalidado",
            "Se eliminó tu certificado actual. Deberás generar uno nuevo la próxima vez "
            "que inicies sesión.",
        )

    # --- Contraseña (Abogado) ---------------------------------------------------

    def _build_password_box(self) -> QGroupBox:
        box = QGroupBox("Cambiar contraseña")
        layout = QVBoxLayout(box)

        layout.addWidget(QLabel("Contraseña actual:"))
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.current_password_input)

        layout.addWidget(QLabel("Nueva contraseña:"))
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_password_input)

        layout.addWidget(QLabel("Confirmar nueva contraseña:"))
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_password_input)

        change_btn = QPushButton("Cambiar contraseña")
        change_btn.clicked.connect(self._on_change_password)
        layout.addWidget(change_btn)
        return box

    def _on_change_password(self) -> None:
        current = users_repo.get_by_id(self.user.id)
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not current.password_hash or not verify_password(
            current_password, current.password_hash, current.password_salt
        ):
            QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña actual no es válida.")
            return

        if len(new_password) < 6:
            QMessageBox.warning(self, "Contraseña inválida", "La nueva contraseña debe tener al menos 6 caracteres.")
            return
        if new_password != confirm_password:
            QMessageBox.warning(self, "Contraseña inválida", "Las contraseñas no coinciden.")
            return

        pwd_hash, salt = hash_password(new_password)
        users_repo.set_password(current.id, password_hash=pwd_hash, password_salt=salt, must_change_password=False)

        self.current_password_input.clear()
        self.new_password_input.clear()
        self.confirm_password_input.clear()

        QMessageBox.information(self, "Contraseña actualizada", "Tu contraseña se actualizó correctamente.")
