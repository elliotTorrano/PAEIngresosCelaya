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

TAB_GENERAR_REQUERIMIENTO = "Generar Formato Requerimiento"
TAB_GENERAR_MANDAMIENTO = "Generar Formato Mandamiento"
TAB_REVISAR_REQUERIMIENTO = "Revisar Formato Requerimiento"
TAB_REVISAR_MANDAMIENTO = "Revisar Formato Mandamiento"


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
        self._viendo_como_widgets: dict[str, QWidget] = {}
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
            from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView
            from app.ui.agente.requerimientos_revision_view import RequerimientosRevisionView

            self._add_permanent_tab(
                RequerimientosGenerarView(self.user), f"{TAB_GENERAR_REQUERIMIENTO} (Agente del PAE)"
            )
            revision_widget = RequerimientosRevisionView(self.user)
            revision_widget.archivo_cambiado.connect(
                lambda filename: self._on_revision_filename_changed(revision_widget, filename)
            )
            self._add_permanent_tab(revision_widget, f"{TAB_REVISAR_REQUERIMIENTO} (Agente del PAE)")

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

        if role == ROLE_AGENTE_PAE:
            self._build_seguimiento_menu()

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
        if self.user.role == ROLE_AGENTE_PAE:
            # Dos pantallas separadas (no una sola con todo apilado) para que
            # generar el formato para el Abogado y revisar lo que el Abogado
            # devolvió no se interrumpan visualmente entre sí. Cada una, a su
            # vez, se agrupa por tipo de documento (Requerimiento/Mandamiento)
            # -- Mandamiento todavía no está desarrollado, pero el menú y la
            # pestaña ya quedan preparados para cuando se implemente.
            generar_menu = menu.addMenu("Generar Formato")
            generar_req_action = generar_menu.addAction("Requerimiento")
            generar_req_action.triggered.connect(self._show_generar_formato_tab)
            generar_mand_action = generar_menu.addAction("Mandamiento (Próximamente)")
            generar_mand_action.triggered.connect(self._show_generar_mandamiento_tab)

            revisar_menu = menu.addMenu("Revisar Formato")
            revisar_req_action = revisar_menu.addAction("Requerimiento")
            revisar_req_action.triggered.connect(self._show_revisar_formato_tab)
            revisar_mand_action = revisar_menu.addAction("Mandamiento (Próximamente)")
            revisar_mand_action.triggered.connect(self._show_revisar_mandamiento_tab)
        else:
            req_action = menu.addAction("Formato de Requerimientos")
            req_action.triggered.connect(self._show_requerimientos_tab)
            mandamientos_action = menu.addAction("Mandamientos (próximamente)")
            mandamientos_action.triggered.connect(self._show_mandamientos_tab)

    def _show_requerimientos_tab(self) -> None:
        """Sólo para el Abogado -- el Agente del PAE usa las pantallas
        separadas: ver `_show_generar_formato_tab` y `_show_revisar_formato_tab`."""
        widget = self._formato_widgets.get("requerimientos")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView

            widget = RequerimientosCaptureView(self.user)
            self.tabs.addTab(widget, "Formato de Requerimientos (Abogado)")
            self._formato_widgets["requerimientos"] = widget
        self.tabs.setCurrentWidget(widget)

    def _show_generar_formato_tab(self) -> None:
        widget = self._formato_widgets.get("generar_formato")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView

            widget = RequerimientosGenerarView(self.user)
            self.tabs.addTab(widget, TAB_GENERAR_REQUERIMIENTO)
            self._formato_widgets["generar_formato"] = widget
        self.tabs.setCurrentWidget(widget)

    def _show_revisar_formato_tab(self) -> None:
        widget = self._formato_widgets.get("revisar_formato")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.agente.requerimientos_revision_view import RequerimientosRevisionView

            widget = RequerimientosRevisionView(self.user)
            widget.archivo_cambiado.connect(
                lambda filename, w=widget: self._on_revision_filename_changed(w, filename)
            )
            self.tabs.addTab(widget, TAB_REVISAR_REQUERIMIENTO)
            self._formato_widgets["revisar_formato"] = widget
        self.tabs.setCurrentWidget(widget)

    def _on_revision_filename_changed(self, widget: QWidget, filename: str) -> None:
        index = self.tabs.indexOf(widget)
        if index == -1:
            return
        base_title = widget.property("base_tab_title")
        if base_title is None:
            base_title = self.tabs.tabText(index)
            widget.setProperty("base_tab_title", base_title)
        self.tabs.setTabText(index, f"{base_title} — {filename}" if filename else base_title)

    def _show_generar_mandamiento_tab(self) -> None:
        self._show_placeholder_tab("generar_mandamiento", TAB_GENERAR_MANDAMIENTO)

    def _show_revisar_mandamiento_tab(self) -> None:
        self._show_placeholder_tab("revisar_mandamiento", TAB_REVISAR_MANDAMIENTO)

    def _show_mandamientos_tab(self) -> None:
        self._show_placeholder_tab("mandamientos", "Mandamientos (próximamente)")

    def _show_placeholder_tab(self, key: str, title: str) -> None:
        widget = self._formato_widgets.get(key)
        if widget is None or self.tabs.indexOf(widget) == -1:
            widget = QLabel(
                "El Formato de Mandamientos y los Reportes de Requerimientos/Mandamientos "
                "se agregarán en una siguiente fase del programa."
            )
            widget.setWordWrap(True)
            widget.setContentsMargins(16, 16, 16, 16)
            self.tabs.addTab(widget, title)
            self._formato_widgets[key] = widget
        self.tabs.setCurrentWidget(widget)

    # --- Menú "Seguimiento" (sólo Agente del PAE) -----------------------------------

    def _build_seguimiento_menu(self) -> None:
        menu = self.menuBar().addMenu("Seguimiento")
        action = menu.addAction("Ver seguimiento")
        action.triggered.connect(self._show_seguimiento_tab)

    def _show_seguimiento_tab(self) -> None:
        widget = self._otros_widgets.get("seguimiento")
        if widget is None or self.tabs.indexOf(widget) == -1:
            from app.ui.agente.seguimiento_view import SeguimientoView

            widget = SeguimientoView(self.user)
            widget.continuar_revision_solicitada.connect(self._on_continuar_revision_solicitada)
            self.tabs.addTab(widget, "Seguimiento")
            self._otros_widgets["seguimiento"] = widget
        self.tabs.setCurrentWidget(widget)

    def _on_continuar_revision_solicitada(self, revision_import_id: int) -> None:
        self._show_revisar_formato_tab()
        self._formato_widgets["revisar_formato"]._load_import(revision_import_id)

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
        if target.role == ROLE_AGENTE_PAE:
            from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView
            from app.ui.agente.requerimientos_revision_view import RequerimientosRevisionView

            generar_key = f"generar:{target.id}"
            generar_widget = self._viendo_como_widgets.get(generar_key)
            if generar_widget is None or self.tabs.indexOf(generar_widget) == -1:
                generar_widget = RequerimientosGenerarView(target, simulate=True)
                self.tabs.addTab(
                    generar_widget, f"Viendo como: {target.full_name} — {TAB_GENERAR_REQUERIMIENTO}"
                )
                self._viendo_como_widgets[generar_key] = generar_widget

            revisar_key = f"revisar:{target.id}"
            revisar_widget = self._viendo_como_widgets.get(revisar_key)
            if revisar_widget is None or self.tabs.indexOf(revisar_widget) == -1:
                revisar_widget = RequerimientosRevisionView(target, simulate=True)
                revisar_widget.archivo_cambiado.connect(
                    lambda filename, w=revisar_widget: self._on_revision_filename_changed(w, filename)
                )
                self.tabs.addTab(
                    revisar_widget, f"Viendo como: {target.full_name} — {TAB_REVISAR_REQUERIMIENTO}"
                )
                self._viendo_como_widgets[revisar_key] = revisar_widget

            self.tabs.setCurrentWidget(generar_widget)
        else:
            from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView

            key = f"abogado:{target.id}"
            widget = self._viendo_como_widgets.get(key)
            if widget is None or self.tabs.indexOf(widget) == -1:
                widget = RequerimientosCaptureView(target, simulate=True)
                self.tabs.addTab(widget, f"Viendo como: {target.full_name}")
                self._viendo_como_widgets[key] = widget
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
