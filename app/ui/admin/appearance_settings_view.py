"""Personalización del ícono de la ventana y el fondo de la interfaz (sólo Administrador)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.db.repositories import settings as settings_repo
from app.db.repositories.users import User
from app.ui.widgets.styles import apply_window_background
from app.utils.paths import appearance_dir


class AppearanceSettingsView(QWidget):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Estos cambios se aplican de inmediato en esta computadora. Si el "
            "programa se distribuye a otros equipos, cada uno mantiene su propia "
            "apariencia salvo que se vuelva a copiar la instalación completa."
        ))

        icon_btn = QPushButton("Cambiar ícono del programa (.ico/.png)")
        icon_btn.clicked.connect(self._on_change_icon)
        layout.addWidget(icon_btn)

        bg_image_btn = QPushButton("Cambiar imagen de fondo")
        bg_image_btn.clicked.connect(self._on_change_background_image)
        layout.addWidget(bg_image_btn)

        bg_color_btn = QPushButton("Cambiar color de fondo")
        bg_color_btn.clicked.connect(self._on_change_background_color)
        layout.addWidget(bg_color_btn)

        layout.addStretch()

    def _on_change_icon(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar ícono", "", "Íconos (*.ico *.png)")
        if not file_path:
            return
        dest = appearance_dir() / f"icon{Path(file_path).suffix}"
        shutil.copyfile(file_path, dest)
        settings_repo.set(settings_repo.KEY_ICON_PATH, str(dest))

        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(QIcon(str(dest)))
        QMessageBox.information(self, "Ícono actualizado", "El ícono se aplicó a esta sesión.")

    def _on_change_background_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen de fondo", "", "Imágenes (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        dest = appearance_dir() / f"background{Path(file_path).suffix}"
        shutil.copyfile(file_path, dest)
        settings_repo.set(settings_repo.KEY_BACKGROUND_PATH, str(dest))
        settings_repo.set(settings_repo.KEY_BACKGROUND_COLOR, None)
        self._refresh_background()

    def _on_change_background_color(self) -> None:
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        settings_repo.set(settings_repo.KEY_BACKGROUND_COLOR, color.name())
        settings_repo.set(settings_repo.KEY_BACKGROUND_PATH, None)
        self._refresh_background()

    def _refresh_background(self) -> None:
        top_level = self.window()
        apply_window_background(top_level)
        QMessageBox.information(self, "Fondo actualizado", "El fondo se aplicó a esta sesión.")
