"""Ventana de inicio de sesión: usuario/contraseña (Abogado) o certificado (los demás roles)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.auth import session
from app.auth.cert_auth import verify_certificate_file
from app.auth.passwords import verify_password
from app.auth.recovery_codes import ROLES_WITH_RECOVERY_CODE
from app.config import AUTH_TYPE_CERTIFICADO, window_title
from app.db.repositories import users as users_repo
from app.ui.login.change_password_dialog import ChangePasswordDialog
from app.ui.login.enrollment_dialog import EnrollmentDialog
from app.ui.login.forgot_password_dialog import ForgotPasswordDialog
from app.ui.login.import_update_dialog import ImportUpdateDialog
from app.ui.login.recovery_code_dialog import RecoveryCodeRecoveryDialog
from app.ui.widgets.background_widget import BackgroundWidget
from app.ui.widgets.styles import apply_base_style, login_background_path

WELCOME_TITLE = (
    "Bienvenido/a al Sistema de Control del Proceso Administrativo de "
    "Ejecución del Municipio de Celaya, Gto."
)
WELCOME_SUBTITLE = "Por favor, ingrese su usuario y posteriormente su certificado."


class LoginWindow(QDialog):
    """Nota sobre botones "default": deliberadamente NINGÚN botón usa
    setDefault()/setAutoDefault(). Qt sólo permite un botón "default" activo
    por diálogo, sin importar cuál página del QStackedWidget esté visible --
    con 3 páginas cada una llamando setDefault(True), sólo la última ganaba
    (la del certificado), y Enter en cualquier otra página disparaba ADEMÁS
    esa acción oculta (p. ej. "Falta el certificado" en segundo plano),
    dejando la ventana como congelada. Cada campo ya dispara su acción via
    returnPressed, y los botones vía clicked -- no hace falta setDefault."""

    def __init__(self, parent=None):
        super().__init__(parent)
        apply_base_style(self)
        self.setWindowTitle(window_title("Iniciar sesión"))
        self.setMinimumSize(480, 420)
        self._user: users_repo.User | None = None
        self._cert_path: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        background = BackgroundWidget()
        background.set_image_path(login_background_path())
        # Fondo semi-opaco para CUALQUIER QLabel que cuelgue de esta ventana --
        # sin esto, el texto de las 3 páginas (usuario, contraseña, certificado)
        # se pinta directamente sobre la imagen de fondo y se pierde en las
        # zonas claras del escudo. Los QLabel de bienvenida, más abajo, tienen
        # su propio setStyleSheet (más ancho de relleno) que gana sobre esta regla.
        background.setStyleSheet(
            "QLabel { background-color: rgba(255, 255, 255, 0.85); padding: 2px 4px; border-radius: 3px; }"
        )
        bg_layout = QVBoxLayout(background)
        bg_layout.setContentsMargins(16, 16, 16, 16)

        welcome_title = QLabel(WELCOME_TITLE)
        welcome_title.setWordWrap(True)
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_subtitle = QLabel(WELCOME_SUBTITLE)
        welcome_subtitle.setWordWrap(True)
        welcome_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for label in (welcome_title, welcome_subtitle):
            label.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.85); padding: 6px; border-radius: 4px;"
            )
        bg_layout.addWidget(welcome_title)
        bg_layout.addWidget(welcome_subtitle)

        self.stack = QStackedWidget()
        bg_layout.addWidget(self.stack)

        self.stack.addWidget(self._build_username_page())
        self.stack.addWidget(self._build_password_page())
        self.stack.addWidget(self._build_cert_page())

        links = QHBoxLayout()
        forgot_link = QPushButton("Olvidé mi contraseña o certificado")
        forgot_link.setFlat(True)
        forgot_link.clicked.connect(self._on_forgot_password)
        import_link = QPushButton("Importar actualización del administrador")
        import_link.setFlat(True)
        import_link.clicked.connect(self._on_import_update)
        links.addWidget(forgot_link)
        links.addWidget(import_link)
        bg_layout.addLayout(links)

        outer.addWidget(background)

    # --- Página 1: usuario -----------------------------------------------------
    def _build_username_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Usuario:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        continue_btn = QPushButton("Continuar")
        continue_btn.clicked.connect(self._on_continue)
        layout.addWidget(continue_btn)

        self.username_input.returnPressed.connect(self._on_continue)
        return page

    def _on_continue(self) -> None:
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Falta información", "Escriba su usuario.")
            return

        user = users_repo.get_by_username(username)
        if user is None or not user.active:
            QMessageBox.warning(self, "Usuario no encontrado", "Usuario inválido o inactivo en esta instalación.")
            return

        self._user = user
        if user.auth_type == AUTH_TYPE_CERTIFICADO:
            if not users_repo.has_certificate(user):
                self._run_enrollment(user)
            else:
                self.recovery_code_btn.setVisible(user.role in ROLES_WITH_RECOVERY_CODE)
                self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(1)

    def _on_back_to_username(self) -> None:
        self._user = None
        self._cert_path = None
        self.password_input.clear()
        self.cert_password_input.clear()
        self.cert_path_label.setText("(ninguno seleccionado)")
        self.username_input.clear()
        self.stack.setCurrentIndex(0)
        # setFocus() inmediato no siempre se aplica aquí -- en particular si
        # justo antes se cerró un QFileDialog nativo (p. ej. "Regresar" tras
        # cancelar la selección del certificado), la reactivación de la
        # ventana todavía no terminó de procesarse y el foco se queda en
        # ningún lado: Enter deja de disparar returnPressed aunque el clic
        # del mouse en "Continuar" sí funcione. Diferirlo con singleShot(0)
        # lo aplica después de que esos eventos pendientes se procesen.
        QTimer.singleShot(0, self.username_input.setFocus)

    # --- Página 2: usuario + contraseña (Abogado) -------------------------------
    def _build_password_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Contraseña:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        login_btn = QPushButton("Iniciar sesión")
        login_btn.setProperty("role", "primary")
        login_btn.clicked.connect(self._on_login_password)
        layout.addWidget(login_btn)

        back_btn = QPushButton("Regresar")
        back_btn.setFlat(True)
        back_btn.clicked.connect(self._on_back_to_username)
        layout.addWidget(back_btn)

        self.password_input.returnPressed.connect(self._on_login_password)
        return page

    def _on_login_password(self) -> None:
        user = self._user
        password = self.password_input.text()
        if not user.password_hash or not verify_password(password, user.password_hash, user.password_salt):
            QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña no es válida.")
            return

        if user.must_change_password:
            change_dialog = ChangePasswordDialog(user, parent=self)
            if change_dialog.exec() != QDialog.DialogCode.Accepted:
                self.stack.setCurrentIndex(0)
                return
            user = users_repo.get_by_id(user.id)

        self._finish_login(user)

    # --- Página 3: certificado (Súper-usuario/Administrador/Agente) ------------
    def _build_cert_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Archivo de certificado (.pfx):"))
        cert_row = QHBoxLayout()
        self.cert_path_label = QLabel("(ninguno seleccionado)")
        browse_btn = QPushButton("Examinar...")
        browse_btn.clicked.connect(self._on_browse_cert)
        cert_row.addWidget(self.cert_path_label)
        cert_row.addWidget(browse_btn)
        layout.addLayout(cert_row)

        layout.addWidget(QLabel("Contraseña del certificado:"))
        self.cert_password_input = QLineEdit()
        self.cert_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.cert_password_input)

        login_btn = QPushButton("Iniciar sesión")
        login_btn.setProperty("role", "primary")
        login_btn.clicked.connect(self._on_login_cert)
        layout.addWidget(login_btn)

        self.recovery_code_btn = QPushButton("¿Perdió o dañó su certificado? Recuperar con código de respaldo")
        self.recovery_code_btn.setFlat(True)
        self.recovery_code_btn.clicked.connect(self._on_recover_with_code)
        self.recovery_code_btn.setVisible(False)
        layout.addWidget(self.recovery_code_btn)

        back_btn = QPushButton("Regresar")
        back_btn.setFlat(True)
        back_btn.clicked.connect(self._on_back_to_username)
        layout.addWidget(back_btn)

        self.cert_password_input.returnPressed.connect(self._on_login_cert)
        return page

    def _on_recover_with_code(self) -> None:
        user = self._user
        dialog = RecoveryCodeRecoveryDialog(user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.recovered:
            QMessageBox.information(
                self, "Acceso recuperado",
                "Se eliminó el certificado anterior. A continuación genere uno nuevo "
                "(incluido un nuevo código de respaldo).",
            )
            self._run_enrollment(users_repo.get_by_id(user.id))

    def _on_browse_cert(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar certificado", "", "Certificado (*.pfx)")
        if file_path:
            self._cert_path = file_path
            self.cert_path_label.setText(file_path)

    def _on_login_cert(self) -> None:
        user = self._user
        if not self._cert_path:
            QMessageBox.warning(self, "Falta el certificado", "Seleccione su archivo .pfx.")
            return

        password = self.cert_password_input.text()
        ok, message = verify_certificate_file(user, Path(self._cert_path), password)
        if not ok:
            QMessageBox.warning(self, "No se pudo iniciar sesión", message)
            return

        self._finish_login(user)

    # --- Enrolamiento (primer login de un usuario de certificado) --------------
    def _run_enrollment(self, user: users_repo.User) -> None:
        dialog = EnrollmentDialog(user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._finish_login(users_repo.get_by_id(user.id))
        elif dialog.deferred:
            # "Generar después": sin certificado no hay con qué continuar
            # ahora, así que se cierra la sesión de inmediato (el programa
            # termina limpio; ver el ciclo en app/main.py).
            self.reject()
        else:
            self.stack.setCurrentIndex(0)

    # --- Enlaces -----------------------------------------------------------------
    def _on_forgot_password(self) -> None:
        dialog = ForgotPasswordDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Especificación: tras generar la solicitud, el programa se cierra.
            self.reject()
            os._exit(0)

    def _on_import_update(self) -> None:
        ImportUpdateDialog(parent=self).exec()

    def _finish_login(self, user: users_repo.User) -> None:
        session.start(user)
        self.accept()

    @property
    def logged_in_user(self) -> users_repo.User | None:
        return session.current()
