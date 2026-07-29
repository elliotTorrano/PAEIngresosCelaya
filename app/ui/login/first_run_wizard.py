"""Asistente de primer arranque: crea el súper-usuario y el primer Administrador.

Sólo se corre una vez, cuando la base de datos está vacía. Los certificados de
ambas cuentas se generan después, en su primer inicio de sesión real.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth import first_run


class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración inicial — Sistema PAE")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Esta es la primera vez que se ejecuta el programa en este equipo.\n"
                "Se debe crear la cuenta de Súper-usuario y la del primer Administrador."
            )
        )

        layout.addWidget(QLabel("<b>Súper-usuario</b>"))
        self.su_username = QLineEdit()
        self.su_username.setPlaceholderText("Usuario")
        self.su_fullname = QLineEdit()
        self.su_fullname.setPlaceholderText("Nombre completo")
        self.su_email = QLineEdit()
        self.su_email.setPlaceholderText("Correo electrónico")
        for w in (self.su_username, self.su_fullname, self.su_email):
            layout.addWidget(w)

        layout.addWidget(QLabel("<b>Primer Administrador</b>"))
        self.admin_username = QLineEdit()
        self.admin_username.setPlaceholderText("Usuario")
        self.admin_fullname = QLineEdit()
        self.admin_fullname.setPlaceholderText("Nombre completo")
        self.admin_email = QLineEdit()
        self.admin_email.setPlaceholderText("Correo electrónico")
        for w in (self.admin_username, self.admin_fullname, self.admin_email):
            layout.addWidget(w)

        create_btn = QPushButton("Crear cuentas")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)

    def _on_create(self) -> None:
        fields = {
            "Usuario del súper-usuario": self.su_username.text().strip(),
            "Nombre del súper-usuario": self.su_fullname.text().strip(),
            "Correo del súper-usuario": self.su_email.text().strip(),
            "Usuario del administrador": self.admin_username.text().strip(),
            "Nombre del administrador": self.admin_fullname.text().strip(),
            "Correo del administrador": self.admin_email.text().strip(),
        }
        missing = [label for label, value in fields.items() if not value]
        if missing:
            QMessageBox.warning(self, "Datos incompletos", "Falta: " + ", ".join(missing))
            return

        if self.su_username.text().strip() == self.admin_username.text().strip():
            QMessageBox.warning(self, "Usuarios inválidos", "El súper-usuario y el administrador deben tener nombres de usuario distintos.")
            return

        try:
            first_run.create_superuser(
                username=self.su_username.text().strip(),
                full_name=self.su_fullname.text().strip(),
                email=self.su_email.text().strip(),
            )
            first_run.create_first_administrator(
                username=self.admin_username.text().strip(),
                full_name=self.admin_fullname.text().strip(),
                email=self.admin_email.text().strip(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al crear las cuentas", str(exc))
            return

        QMessageBox.information(
            self,
            "Cuentas creadas",
            "Las cuentas fueron creadas. Ahora inicie sesión con el usuario del súper-usuario "
            "o del administrador para generar su certificado.",
        )
        self.accept()
