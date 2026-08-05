"""Token de escritura del directorio remoto de usuarios (Turso) -- sólo
Administrador/Súper-usuario. A diferencia del token de solo lectura (que va
horneado en el instalador de todos, ver app/sync/config.py), este token
tiene permiso de escritura y por eso se guarda únicamente en la base local
de esta computadora (app_settings), nunca en el instalador."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.config import ROLE_ABOGADO, ROLE_AGENTE_PAE, ROLE_REPORTEADOR
from app.db.repositories import settings as settings_repo
from app.db.repositories import users as users_repo
from app.db.repositories.users import User
from app.sync import user_directory


class SyncSettingsView(QWidget):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Token de escritura del directorio remoto de usuarios (Turso). "
            "Se guarda solo en esta computadora -- nunca viaja con el instalador. "
            "Con él, las cuentas de Agente/Abogado/Reporteador que se den de alta "
            "aquí aparecen automáticamente en cualquier otra instalación con internet."
        ))

        self.token_input = QLineEdit(settings_repo.get(settings_repo.KEY_TURSO_WRITE_TOKEN) or "")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Token de escritura de Turso")
        layout.addWidget(self.token_input)

        save_btn = QPushButton("Guardar token")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        sync_btn = QPushButton("Sincronizar ahora")
        sync_btn.setToolTip(
            "Sube al directorio remoto todas las cuentas de Agente/Abogado/"
            "Reporteador -- sirve para reintentar si algún alta falló por falta "
            "de conexión, o para las cuentas creadas antes de esta función."
        )
        sync_btn.clicked.connect(self._on_sync_now)
        layout.addWidget(sync_btn)

        layout.addStretch()

    def _on_save(self) -> None:
        token = self.token_input.text().strip()
        settings_repo.set(settings_repo.KEY_TURSO_WRITE_TOKEN, token or None)
        QMessageBox.information(self, "Token guardado", "El token se guardó en esta computadora.")

    def _on_sync_now(self) -> None:
        for role in (ROLE_AGENTE_PAE, ROLE_ABOGADO, ROLE_REPORTEADOR):
            for u in users_repo.list_by_role(role, active_only=False):
                user_directory.push_user(u)
        QMessageBox.information(
            self, "Sincronización",
            "Se intentó subir todas las cuentas al directorio remoto. Si no hay "
            "conexión o el token no está configurado, no pasa nada -- se puede "
            "volver a intentar en cualquier momento.",
        )
