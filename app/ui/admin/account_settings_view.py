"""Cambio de los datos de identidad (usuario/nombre/correo) del Administrador y,
sólo para el Súper-usuario, de sus propios datos.

Cualquier cambio exige confirmar con el certificado ACTUAL de la cuenta
afectada (ver CertificateConfirmDialog) y, al aplicarse, obliga a esa cuenta
a generar un certificado nuevo en su siguiente inicio de sesión.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.auth.recovery_codes import generate_recovery_code, hash_recovery_code
from app.config import ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo
from app.ui.login.recovery_code_dialog import RecoveryCodeDisplayDialog
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog


class AccountSettingsView(QWidget):
    def __init__(self, current_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.current_user = current_user

        layout = QVBoxLayout(self)

        admin = users_repo.get_administrator()
        if admin is not None:
            layout.addWidget(self._build_identity_box("Datos del Administrador", admin))
        else:
            layout.addWidget(QLabel("No hay Administrador configurado en esta instalación."))

        if current_user.role == ROLE_SUPERUSUARIO:
            layout.addWidget(self._build_identity_box("Mis datos (Súper-usuario)", current_user))

        layout.addStretch()

    def _build_identity_box(self, title: str, target_user: users_repo.User) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        layout.addWidget(QLabel("Usuario:"))
        username_input = QLineEdit(target_user.username)
        layout.addWidget(username_input)

        layout.addWidget(QLabel("Nombre completo:"))
        fullname_input = QLineEdit(target_user.full_name)
        layout.addWidget(fullname_input)

        layout.addWidget(QLabel("Correo electrónico:"))
        email_input = QLineEdit(target_user.email or "")
        layout.addWidget(email_input)

        layout.addWidget(
            QLabel(
                "Al guardar, se pedirá el certificado ACTUAL de esta cuenta para confirmar "
                "la identidad; después deberá generarse un certificado nuevo en el siguiente "
                "inicio de sesión de esa cuenta."
            )
        )

        save_btn = QPushButton("Guardar cambios")
        layout.addWidget(save_btn)

        def on_save() -> None:
            new_username = username_input.text().strip()
            new_fullname = fullname_input.text().strip()
            new_email = email_input.text().strip()

            if not new_username or not new_fullname:
                QMessageBox.warning(self, "Datos incompletos", "Usuario y nombre completo son obligatorios.")
                return

            existing = users_repo.get_by_username(new_username)
            if existing is not None and existing.id != target_user.id:
                QMessageBox.warning(self, "Usuario existente", f"Ya existe un usuario '{new_username}'.")
                return

            if not users_repo.has_certificate(target_user):
                QMessageBox.warning(
                    self,
                    "Sin certificado registrado",
                    f"'{target_user.username}' todavía no tiene un certificado generado; debe "
                    "iniciar sesión con esa cuenta al menos una vez antes de poder cambiar sus datos.",
                )
                return

            confirm_dialog = CertificateConfirmDialog(target_user, parent=self)
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                return

            users_repo.update_identity(
                target_user.id, username=new_username, full_name=new_fullname, email=new_email or None
            )
            users_repo.clear_certificate(target_user.id)

            QMessageBox.information(
                self,
                "Datos actualizados",
                f"Se actualizaron los datos de '{new_fullname}'. Deberá generar un certificado "
                "nuevo la próxima vez que esa cuenta inicie sesión.",
            )

        save_btn.clicked.connect(on_save)

        layout.addWidget(
            QLabel(
                "Certificado: genere uno nuevo cuando quiera (por ejemplo, para moverlo a "
                "otra USB), sin necesidad de cambiar usuario/nombre/correo. El certificado "
                "actual queda invalidado de inmediato; se le pedirá generar el nuevo en el "
                "siguiente inicio de sesión de esa cuenta."
            )
        )
        new_cert_btn = QPushButton("Generar nuevo certificado")
        layout.addWidget(new_cert_btn)

        def on_generate_new_certificate() -> None:
            current = users_repo.get_by_id(target_user.id)
            if not users_repo.has_certificate(current):
                QMessageBox.warning(
                    self,
                    "Sin certificado registrado",
                    f"'{current.username}' todavía no tiene un certificado generado; debe "
                    "iniciar sesión con esa cuenta al menos una vez antes de poder generar "
                    "uno nuevo.",
                )
                return

            confirm_dialog = CertificateConfirmDialog(current, parent=self)
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                return

            users_repo.clear_certificate(current.id)

            QMessageBox.information(
                self,
                "Certificado invalidado",
                f"Se eliminó el certificado actual de '{current.full_name}'. Deberá generar uno "
                "nuevo la próxima vez que esa cuenta inicie sesión.",
            )

        new_cert_btn.clicked.connect(on_generate_new_certificate)

        layout.addWidget(
            QLabel(
                "Código de respaldo: permite recuperar el acceso de inmediato si esta "
                "cuenta pierde o daña su certificado, sin depender de que otra persona "
                "lo apruebe. Genere uno nuevo si nunca lo ha guardado, o si sospecha que "
                "el anterior quedó expuesto (invalida el que ya existía)."
            )
        )
        recovery_btn = QPushButton("Generar nuevo código de respaldo")
        layout.addWidget(recovery_btn)

        def on_generate_recovery_code() -> None:
            current = users_repo.get_by_id(target_user.id)
            if not users_repo.has_certificate(current):
                QMessageBox.warning(
                    self,
                    "Sin certificado registrado",
                    f"'{current.username}' todavía no tiene un certificado generado; debe "
                    "iniciar sesión con esa cuenta al menos una vez antes de poder generar "
                    "un código de respaldo.",
                )
                return

            confirm_dialog = CertificateConfirmDialog(current, parent=self)
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                return

            code = generate_recovery_code()
            code_hash, code_salt = hash_recovery_code(code)
            users_repo.set_recovery_code(current.id, recovery_code_hash=code_hash, recovery_code_salt=code_salt)

            RecoveryCodeDisplayDialog(code, parent=self).exec()

        recovery_btn.clicked.connect(on_generate_recovery_code)

        return box
