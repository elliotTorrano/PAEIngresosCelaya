"""Pantalla de Bienvenida: primera pestaña tras iniciar sesión, para
cualquier rol. Muestra la imagen de apariencia (si el Administrador subió
una) a pantalla completa, con proporción preservada."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.db.repositories.users import User
from app.ui.widgets.background_widget import BackgroundWidget


class WelcomeView(QWidget):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.background = BackgroundWidget()
        layout.addWidget(self.background)

        overlay_layout = QVBoxLayout(self.background)
        overlay_layout.addStretch()

        greeting = QLabel(f"Bienvenido/a, {user.full_name}")
        greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        greeting.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.85); border-radius: 8px; "
            "padding: 14px 28px; font-size: 18px; font-weight: 600;"
        )
        overlay_layout.addWidget(greeting, alignment=Qt.AlignmentFlag.AlignHCenter)
        overlay_layout.addStretch()
