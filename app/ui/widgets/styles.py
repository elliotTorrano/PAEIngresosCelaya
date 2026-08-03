"""Aplicación de apariencia (ícono de ventana y fondo) configurable por el Administrador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

from app.db.repositories import settings as settings_repo
from app.ui.widgets import theme
from app.ui.widgets.background_widget import BackgroundWidget
from app.utils.paths import resource_dir

BASE_QSS_PATH = None  # se resuelve en tiempo de ejecución vía resource_dir()


def _base_qss() -> str:
    return theme.render_qss()


def refresh_all_windows_theme() -> None:
    """Vuelve a aplicar la hoja de estilos (con los colores activos ahora
    mismo -- vista previa o guardados, ver app/ui/widgets/theme.py) a TODAS
    las ventanas de nivel superior abiertas en este momento (la MainWindow y
    cualquier diálogo abierto), para que un cambio de color se note de
    inmediato en toda la interfaz sin tener que cerrar y reabrir nada."""
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if not widget.isVisible():
            continue
        central = widget.centralWidget() if hasattr(widget, "centralWidget") else None
        style_target = central if central is not None else widget
        style_target.setStyleSheet(_base_qss())


def apply_base_style(widget: QWidget) -> None:
    """Aplica la hoja de estilos base (paleta institucional) directamente a
    `widget` -- para ventanas que no son la MainWindow (login, diálogos de
    certificado/contraseña/etc.), que no heredan el stylesheet de nadie más
    porque cada QDialog es su propia ventana de nivel superior. A diferencia
    de `apply_window_background`, no toca fondo/ícono -- sólo colores/bordes
    de controles."""
    widget.setStyleSheet(_base_qss())


def default_icon_path() -> Path:
    return resource_dir() / "default_icon.ico"


def default_background_path() -> Path:
    return resource_dir() / "default_background.png"


def login_background_path() -> Path:
    """Imagen de fondo fija de la pantalla de login (escudo del Municipio de
    Celaya) -- a diferencia del fondo general, no es configurable por el
    Administrador."""
    return resource_dir() / "login_background.png"


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
    if bg_path:
        image_path = Path(bg_path)
    elif bg_color:
        # El Administrador eligió explícitamente "sólo color" -- se respeta,
        # no se debe imponer el fondo de fábrica encima.
        image_path = None
    else:
        # Nadie ha configurado apariencia en esta máquina todavía: usar el
        # fondo de fábrica en vez de dejar las ventanas sin imagen.
        image_path = default_background_path()

    for bg_widget in window.findChildren(BackgroundWidget):
        bg_widget.set_image_path(image_path)
        bg_widget.set_color(bg_color)
