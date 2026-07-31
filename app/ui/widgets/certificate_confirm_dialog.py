"""Confirmación de identidad mediante certificado, antes de una operación sensible
(p. ej. cambiar el usuario/nombre/correo del súper-usuario o del Administrador)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth.cert_auth import verify_certificate_file
from app.auth.crypto_certs import load_bundle
from app.config import window_title
from app.db.repositories.users import User


class CertificateConfirmDialog(QDialog):
    """Pide el certificado .pfx + contraseña ACTUALES de `user` y los verifica
    contra lo registrado en la base. Si exec() devuelve Accepted, la
    verificación fue exitosa y `self.private_key` queda disponible -- por
    ejemplo, para firmar algo con esa misma llave sin pedir la contraseña
    una segunda vez."""

    def __init__(self, user: User, parent=None, message: str | None = None):
        super().__init__(parent)
        self.user = user
        self._cert_path: str | None = None
        self.private_key = None
        self.setWindowTitle(window_title(f"Confirmar identidad — {user.full_name}"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                message
                or (
                    f"Para cambiar estos datos, confirme la identidad de '{user.full_name}' con "
                    "su certificado ACTUAL (el que va a reemplazarse por uno nuevo)."
                )
            )
        )

        layout.addWidget(QLabel("Archivo de certificado (.pfx) actual:"))
        cert_row = QHBoxLayout()
        self.cert_path_label = QLabel("(ninguno seleccionado)")
        browse_btn = QPushButton("Examinar...")
        browse_btn.clicked.connect(self._on_browse)
        cert_row.addWidget(self.cert_path_label)
        cert_row.addWidget(browse_btn)
        layout.addLayout(cert_row)

        layout.addWidget(QLabel("Contraseña del certificado:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        confirm_btn = QPushButton("Confirmar identidad")
        confirm_btn.setDefault(True)
        confirm_btn.setAutoDefault(True)
        confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(confirm_btn)

        self.password_input.returnPressed.connect(self._on_confirm)

    def _on_browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar certificado actual", "", "Certificado (*.pfx)")
        if file_path:
            self._cert_path = file_path
            self.cert_path_label.setText(file_path)

    def _on_confirm(self) -> None:
        if not self._cert_path:
            QMessageBox.warning(self, "Falta el certificado", "Seleccione el archivo .pfx actual.")
            return

        pfx_path = Path(self._cert_path)
        password = self.password_input.text()
        ok, message = verify_certificate_file(self.user, pfx_path, password)
        if not ok:
            QMessageBox.warning(self, "No se pudo confirmar", message)
            return

        self.private_key, _certificate = load_bundle(pfx_path.read_bytes(), password)
        self.accept()
