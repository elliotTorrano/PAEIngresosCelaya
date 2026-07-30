"""Generación del certificado en el primer login de un usuario de rol certificado."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth.enrollment import enroll_certificate
from app.db.repositories.users import User
from app.ui.login.recovery_code_dialog import RecoveryCodeDisplayDialog


class EnrollmentDialog(QDialog):
    """Si el usuario cierra este diálogo con "Generar después" (en vez de
    generar el certificado o cancelar con la X), `self.deferred` queda en
    True para que el llamador cierre la sesión de inmediato: sin certificado
    no hay con qué continuar, así que dejarlo a medias no es una opción --
    o se genera ahora, o se sale y se resuelve más tarde."""

    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user
        self.deferred = False
        self.setWindowTitle("Generar certificado de acceso")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Es el primer inicio de sesión de '{user.full_name}'.\n\n"
                "Se generará un certificado digital (archivo .pfx) que deberá usar junto "
                "con la contraseña que elija aquí para iniciar sesión en el futuro.\n\n"
                "Guarde este archivo en un lugar seguro (ej. una USB): sin él no podrá acceder."
            )
        )

        layout.addWidget(QLabel("Contraseña para proteger el certificado:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        layout.addWidget(QLabel("Confirmar contraseña:"))
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_confirm_input)

        generate_btn = QPushButton("Elegir carpeta y generar certificado")
        generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(generate_btn)

        defer_btn = QPushButton("Generar después")
        defer_btn.setFlat(True)
        defer_btn.clicked.connect(self._on_defer)
        layout.addWidget(defer_btn)

    def _on_defer(self) -> None:
        self.deferred = True
        self.reject()

    def _on_generate(self) -> None:
        password = self.password_input.text()
        confirm = self.password_confirm_input.text()

        if len(password) < 6:
            QMessageBox.warning(self, "Contraseña inválida", "La contraseña debe tener al menos 6 caracteres.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Contraseña inválida", "Las contraseñas no coinciden.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta para guardar el certificado")
        if not folder:
            return

        save_path = Path(folder) / f"{self.user.username}.pfx"
        try:
            recovery_code = enroll_certificate(self.user, password=password, save_path=save_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al generar certificado", str(exc))
            return

        QMessageBox.information(
            self,
            "Certificado generado",
            f"Certificado guardado en:\n{save_path}\n\nGuárdelo en un lugar seguro; lo necesitará junto "
            "con su contraseña para iniciar sesión.",
        )

        if recovery_code:
            RecoveryCodeDisplayDialog(recovery_code, parent=self).exec()

        self.accept()
