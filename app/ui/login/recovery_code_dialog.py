"""Diálogos del código de respaldo (Súper-usuario/Administrador): mostrarlo
una sola vez al generarse, y capturarlo para recuperar el acceso sin
depender de la aprobación de otro usuario."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth.recovery_codes import verify_recovery_code
from app.config import window_title
from app.db.repositories import users as users_repo
from app.db.repositories.users import User


class RecoveryCodeDisplayDialog(QDialog):
    """Muestra el código de respaldo recién generado. No se vuelve a mostrar
    después de cerrar este diálogo -- sólo queda su hash en la base."""

    def __init__(self, code: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title("Código de respaldo"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Guarde este código en un lugar seguro y distinto a esta computadora "
                "(por ejemplo, impreso y guardado bajo llave). Es la única forma de "
                "recuperar el acceso de inmediato si en el futuro pierde o daña su "
                "certificado, sin depender de que otra persona lo apruebe.\n\n"
                "Este código NO se volverá a mostrar."
            )
        )

        code_input = QLineEdit(code)
        code_input.setReadOnly(True)
        code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = code_input.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        code_input.setFont(font)
        layout.addWidget(code_input)

        copy_btn = QPushButton("Copiar al portapapeles")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(code))
        layout.addWidget(copy_btn)

        close_btn = QPushButton("Ya lo guardé en un lugar seguro")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class RecoveryCodeRecoveryDialog(QDialog):
    """Pide el código de respaldo de `user` y, si es válido, limpia su
    certificado (`recovered = True` al aceptar) para que pueda reenrolar de
    inmediato. Todo ocurre localmente, sin generar ninguna solicitud."""

    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user
        self.recovered = False
        self.setWindowTitle(window_title("Recuperar con código de respaldo"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Si '{user.full_name}' guardó un código de respaldo al generar su "
                "certificado, escríbalo aquí para recuperar el acceso de inmediato, "
                "sin necesitar la ayuda de otro usuario."
            )
        )

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        layout.addWidget(self.code_input)

        confirm_btn = QPushButton("Verificar código")
        confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(confirm_btn)

        self.code_input.returnPressed.connect(self._on_confirm)

    def _on_confirm(self) -> None:
        code = self.code_input.text()
        if not code.strip():
            QMessageBox.warning(self, "Falta información", "Escriba el código de respaldo.")
            return

        if not verify_recovery_code(self.user, code):
            QMessageBox.warning(self, "Código incorrecto", "El código de respaldo no es válido.")
            return

        users_repo.clear_certificate(self.user.id)
        self.recovered = True
        self.accept()
