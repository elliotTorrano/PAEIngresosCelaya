"""Ventana principal: navegación por pestañas según el rol de la sesión activa."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QMainWindow, QMessageBox, QTabBar, QTabWidget, QVBoxLayout, QWidget

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
    window_title,
)
from app.db.repositories.users import User
from app.ui.widgets.background_widget import BackgroundWidget
from app.ui.widgets.styles import apply_window_background
from app.ui.widgets.welcome_view import WelcomeView


class MainWindow(QMainWindow):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.setWindowTitle(window_title(f"{ROLE_LABELS[user.role]}: {user.full_name}"))
        self.resize(1100, 720)

        self._background = BackgroundWidget()
        bg_layout = QVBoxLayout(self._background)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        bg_layout.addWidget(self.tabs)
        self.setCentralWidget(self._background)

        self._formato_widgets: dict[str, QWidget] = {}
        self._otros_widgets: dict[str, QWidget] = {}
        self._viendo_como_widgets: dict[int, QWidget] = {}
        self._build_tabs()

        apply_window_background(self)

        menu = self.menuBar().addMenu("Sesión")
        logout_action = menu.addAction("Cerrar sesión")
        logout_action.triggered.connect(self._on_logout)
        about_action = menu.addAction("Acerca de")
        about_action.triggered.connect(self._on_about)

    # --- Construcción de pestañas -------------------------------------------------

    def _add_permanent_tab(self, widget: QWidget, title: str) -> None:
        """Pestaña fija que no se puede cerrar (siempre visible mientras dure la sesión)."""
        index = self.tabs.addTab(widget, title)
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, None)

    def _build_tabs(self) -> None:
        role = self.user.role

        self._add_permanent_tab(WelcomeView(self.user), "Bienvenida")

        if role in ROLES_CAN_ACT_AS_AGENTE:
            from app.ui.agente.requerimientos_import_view import RequerimientosImportView

            self._add_permanent_tab(
                RequerimientosImportView(self.user), "Formato de Requerimientos (Agente del PAE)"
            )

        if role in (ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO):
            from app.ui.admin.account_settings_view import AccountSettingsView
            from app.ui.admin.audit_view import AuditView
            from app.ui.admin.user_management_view import UserManagementView
            from app.ui.admin.appearance_settings_view import AppearanceSettingsView
            from app.ui.admin.reset_requests_view import ResetRequestsView

            self._add_permanent_tab(UserManagementView(self.user), "Usuarios")
            self._add_permanent_tab(ResetRequestsView(self.user), "Solicitudes de reset")
            self._add_permanent_tab(AppearanceSettingsView(self.user), "Apariencia")
            self._add_permanent_tab(AccountSettingsView(self.user), "Datos de cuenta")
            self._add_permanent_tab(AuditView(self.user), "Trazabilidad")

        if role in (ROLE_AGENTE_PAE, ROLE_ABOGADO):
            self._build_formato_menu()
            self._build_otros_menu()
            self._build_historico_menu()

        if role == ROLE_SUPERUSUARIO:
            self._build_ver_como_menu()

    def _on_tab_close_requested(self, index: int) -> None:
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        for mapping in (self._formato_widgets, self._otros_widgets, self._viendo_como_widgets):
            for key, tracked in list(mapping.items()):
                if tracked is widget:
                    del mapping[key]
        widget.deleteLater()

    # --- Menú "Formato" (Agente del PAE / Abogado) ---------------------------------

    def _build_formato_menu(self) -> None:
        menu = self.menuBar().addMenu("Formato")
        req_action = menu.addAction("Formato de Requerimientos")
        req_action.triggered.connect(self._show_requerimientos_tab)
        mandamientos_action = menu.addAction("Mandamientos (próximamente)")
        mandamientos_action.triggered.connect(self._show_mandamientos_tab)

    def _show_requerimientos_tab(self) -> None:
        widget = self._formato_widgets.get("requerimientos")
        if widget is None or self.tabs.indexOf(widget) == -1:
            if self.user.role == ROLE_AGENTE_PAE:
                from app.ui.agente.requerimientos_import_view import RequerimientosImportView

                widget = RequerimientosImportView(self.user)
                title = "Formato de Requerimientos (Agente del PAE)"
            else:
                from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView

                widget = RequerimientosCaptureView(self.user)
                title = "Formato de Requerimientos (Abogado)"
            self.tabs.addTab(widget, title)
            self._formato_widgets["requerimientos"] = widget
        self.tabs.setCurrentWidget(widget)

    def _show_mandamientos_tab(self) -> None:
        widget = self._formato_widgets.get("mandamientos")
        if widget is None or self.tabs.indexOf(widget) == -1:
            widget = QLabel(
                "El Formato de Mandamientos y los Reportes de Requerimientos/Mandamientos "
                "se agregarán en una siguiente fase del programa."
            )
            widget.setWordWrap(True)
            widget.setContentsMargins(16, 16, 16, 16)
            self.tabs.addTab(widget, "Mandamientos (próximamente)")
            self._formato_widgets["mandamientos"] = widget
        self.tabs.setCurrentWidget(widget)

    # --- Menú "Otros" (Agente del PAE / Abogado) ------------------------------------

    def _build_otros_menu(self) -> None:
        menu = self.menuBar().addMenu("Otros")
        action = menu.addAction("Datos de cuenta")
        action.triggered.connect(self._show_datos_cuenta_tab)

    def _show_datos_cuenta_tab(self) -> None:
        widget = self._otros_widgets.get("datos_cuenta")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.widgets.simple_account_view import SimpleAccountView

            widget = SimpleAccountView(self.user)
            self.tabs.addTab(widget, "Datos de cuenta")
            self._otros_widgets["datos_cuenta"] = widget
        self.tabs.setCurrentWidget(widget)

    # --- Menú "Histórico" (Agente del PAE / Abogado) --------------------------------

    def _build_historico_menu(self) -> None:
        menu = self.menuBar().addMenu("Histórico")
        action = menu.addAction("Ver histórico")
        action.triggered.connect(self._show_historico_tab)

    def _show_historico_tab(self) -> None:
        widget = self._otros_widgets.get("historico")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.widgets.historico_view import HistoricoView

            widget = HistoricoView(self.user)
            self.tabs.addTab(widget, "Histórico")
            self._otros_widgets["historico"] = widget
        self.tabs.setCurrentWidget(widget)

    # --- Menú "Ver como" (sólo Súper-usuario) ---------------------------------------

    def _build_ver_como_menu(self) -> None:
        menu = self.menuBar().addMenu("Ver como")
        action = menu.addAction("Elegir agente o abogado...")
        action.triggered.connect(self._on_choose_view_as)

    def _on_choose_view_as(self) -> None:
        from app.ui.widgets.choose_user_dialog import ChooseUserDialog

        dialog = ChooseUserDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selected_user is None:
            return

        target = dialog.selected_user
        widget = self._viendo_como_widgets.get(target.id)
        if widget is None or self.tabs.indexOf(widget) == -1:
            if target.role == ROLE_AGENTE_PAE:
                from app.ui.agente.requerimientos_import_view import RequerimientosImportView

                widget = RequerimientosImportView(target, simulate=True)
            else:
                from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView

                widget = RequerimientosCaptureView(target, simulate=True)
            self.tabs.addTab(widget, f"Viendo como: {target.full_name}")
            self._viendo_como_widgets[target.id] = widget
        self.tabs.setCurrentWidget(widget)

    def _on_logout(self) -> None:
        session.end()
        self.close()

    def _on_about(self) -> None:
        QMessageBox.information(
            self, f"Acerca de {APP_NAME}",
            f"{APP_NAME}\nVersión {__version__}\n\nSesión actual: {self.user.full_name} "
            f"({ROLE_LABELS[self.user.role]})",
        )
