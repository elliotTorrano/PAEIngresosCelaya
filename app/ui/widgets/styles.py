"""Aplicación de apariencia (ícono de ventana y fondo) configurable por el Administrador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

from app.db.repositories import settings as settings_repo
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
    qss = _base_qss()

    bg_path = settings_repo.get(settings_repo.KEY_BACKGROUND_PATH)
    bg_color = settings_repo.get(settings_repo.KEY_BACKGROUND_COLOR)

    if bg_path and Path(bg_path).exists():
        image_url = Path(bg_path).as_posix()
        qss += f"\n#appBackground {{ border-image: url({image_url}) 0 0 0 0 stretch stretch; }}\n"
    elif bg_color:
        qss += f"\n#appBackground {{ background-color: {bg_color}; }}\n"

    window.setObjectName("appBackground")
    window.setStyleSheet(qss)
