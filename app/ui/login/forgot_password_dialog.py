"""Solicitud de cambio de contraseña o certificado, enviada al Administrador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.auth import recovery
from app.config import RESET_REASON_LABELS
from app.db.repositories import users as users_repo
from app.utils.paths import reset_requests_dir


class ForgotPasswordDialog(QDialog):
    """Al terminar, el programa se cierra (según lo especificado)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Olvidé mi contraseña o certificado")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Usuario:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Motivo:"))
        self.reason_combo = QComboBox()
        for key, label in RESET_REASON_LABELS.items():
            self.reason_combo.addItem(label, key)
        layout.addWidget(self.reason_combo)

        layout.addWidget(QLabel("Detalle adicional (opcional):"))
        self.detail_input = QPlainTextEdit()
        self.detail_input.setFixedHeight(80)
        layout.addWidget(self.detail_input)

        submit_btn = QPushButton("Generar solicitud y enviar al Administrador")
        submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(submit_btn)

    def _on_submit(self) -> None:
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Falta información", "Indique su usuario.")
            return

        user = users_repo.get_by_username(username)
        if user is None:
            QMessageBox.warning(self, "Usuario no encontrado", f"No existe el usuario '{username}' en esta instalación.")
            return

        admin = users_repo.get_administrator()
        if admin is None or not admin.email:
            QMessageBox.critical(
                self, "Sin Administrador configurado",
                "No hay un Administrador con correo registrado en esta instalación.",
            )
            return

        payload = recovery.build_request_payload(
            username=user.username,
            role=user.role,
            full_name=user.full_name,
            reason=self.reason_combo.currentData(),
            detail=self.detail_input.toPlainText().strip(),
        )

        default_dir = str(reset_requests_dir())
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta para guardar la solicitud", default_dir)
        if not folder:
            return

        request_path = recovery.save_request_file(payload, Path(folder))
        recovery.register_local_request(payload, request_path)

        body = (
            f"Solicitud de {payload['reason']} para el usuario '{user.username}' ({user.full_name}).\n"
            f"Detalle: {payload['detail'] or '(sin detalle)'}\n\n"
            f"Se adjunta el archivo de solicitud generado por el sistema."
        )
        attached = recovery.open_email_client(to_email=admin.email, body=body, attachment_path=request_path)

        if attached:
            note = "Se abrió Outlook con el archivo ya adjunto. Revise y presione Enviar."
        else:
            note = (
                "Se abrió su cliente de correo, pero deberá adjuntar manualmente el archivo guardado en:\n"
                f"{request_path}"
            )

        QMessageBox.information(self, "Solicitud generada", f"{note}\n\nEl programa se cerrará ahora.")
        self.accept()
