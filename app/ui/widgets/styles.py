"""Aplicación de apariencia (ícono de ventana y fondo) configurable por el Administrador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

from app.db.repositories import settings as settings_repo
from app.ui.widgets.background_widget import BackgroundWidget
from app.utils.paths import resource_dir

BASE_QSS_PATH = None  # se resuelve en tiempo de ejecución vía resource_dir()


def _base_qss() -> str:
    path = resource_dir() / "base_style.qss"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def default_icon_path() -> Path:
    return resource_dir() / "default_icon.ico"


def default_background_path() -> Path:
    return resource_dir() / "default_background.png"


def apply_app_icon(app: QApplication) -> None:
    icon_path = settings_repo.get(settings_repo.KEY_ICON_PATH) or str(default_icon_path())
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))


def apply_window_background(window: QWidget) -> None:
    """Aplica la hoja de estilos base y actualiza CADA BackgroundWidget que
    cuelgue de `window` (el fondo general de la ventana y, si está presente,
    el de la pestaña de Bienvenida) con la imagen/color configurados.

    La hoja de estilos se aplica al centralWidget (no a la QMainWindow en sí):
    aplicar CUALQUIER stylesheet directamente sobre una QMainWindow es una causa
    conocida de comportamientos raros del marco nativo en Windows (incluyendo
    que deje de poder redimensionarse a lo largo con el mouse), aunque la regla
    en sí sea inofensiva como un simple background-color."""
    central = window.centralWidget() if hasattr(window, "centralWidget") else None
    style_target = central if central is not None else window
    style_target.setStyleSheet(_base_qss())

    bg_path = settings_repo.get(settings_repo.KEY_BACKGROUND_PATH)
    bg_color = settings_repo.get(settings_repo.KEY_BACKGROUND_COLOR)
    image_path = Path(bg_path) if bg_path else None

    for bg_widget in window.findChildren(BackgroundWidget):
        bg_widget.set_image_path(image_path)
        bg_widget.set_color(bg_color)
