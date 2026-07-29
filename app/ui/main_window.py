"""Ventana principal: navegación por pestañas según el rol de la sesión activa."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QTabWidget

from app.__version__ import __version__
from app.auth import session
from app.config import (
    APP_NAME,
    ROLE_ABOGADO,
    ROLE_ADMINISTRADOR,
    ROLE_AGENTE_PAE,
    ROLE_LABELS,
    ROLE_SUPERUSUARIO,
    ROLES_CAN_ACT_AS_AGENTE,
)
from app.db.repositories.users import User
from app.ui.widgets.styles import apply_window_background


class MainWindow(QMainWindow):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"{APP_NAME} v{__version__} — {ROLE_LABELS[user.role]}: {user.full_name}")
        self.resize(1100, 720)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_tabs()

        apply_window_background(self)

        menu = self.menuBar().addMenu("Sesión")
        logout_action = menu.addAction("Cerrar sesión")
        logout_action.triggered.connect(self._on_logout)
        about_action = menu.addAction("Acerca de")
        about_action.triggered.connect(self._on_about)

    def _build_tabs(self) -> None:
        role = self.user.role

        if role == ROLE_AGENTE_PAE or role in ROLES_CAN_ACT_AS_AGENTE:
            from app.ui.agente.requerimientos_import_view import RequerimientosImportView

            self.tabs.addTab(RequerimientosImportView(self.user), "Formato de Requerimientos (Agente del PAE)")

        if role == ROLE_ABOGADO:
            from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView

            self.tabs.addTab(RequerimientosCaptureView(self.user), "Formato de Requerimientos (Abogado)")

        if role in (ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO):
            from app.ui.admin.account_settings_view import AccountSettingsView
            from app.ui.admin.user_management_view import UserManagementView
            from app.ui.admin.appearance_settings_view import AppearanceSettingsView
            from app.ui.admin.reset_requests_view import ResetRequestsView

            self.tabs.addTab(UserManagementView(self.user), "Usuarios")
            self.tabs.addTab(ResetRequestsView(self.user), "Solicitudes de reset")
            self.tabs.addTab(AppearanceSettingsView(self.user), "Apariencia")
            self.tabs.addTab(AccountSettingsView(self.user), "Datos de cuenta")

        placeholder = QLabel(
            "El Formato de Mandamientos y los Reportes de Requerimientos/Mandamientos "
            "se agregarán en una siguiente fase del programa."
        )
        placeholder.setWordWrap(True)
        placeholder.setContentsMargins(16, 16, 16, 16)
        self.tabs.addTab(placeholder, "Mandamientos y Reportes (próximamente)")

    def _on_logout(self) -> None:
        session.end()
        self.close()

    def _on_about(self) -> None:
        QMessageBox.information(
            self, f"Acerca de {APP_NAME}",
            f"{APP_NAME}\nVersión {__version__}\n\nSesión actual: {self.user.full_name} "
            f"({ROLE_LABELS[self.user.role]})",
        )
