"""Resolución de rutas, consciente de si se corre como script o como .exe (PyInstaller).

El programa es portable: la base de datos y los archivos locales viven junto al
ejecutable (o al script principal en desarrollo), para que la carpeta completa
se pueda copiar de una computadora a otra sin perder nada.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def base_dir() -> Path:
    """Carpeta donde vive el .exe (o el proyecto, en desarrollo)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # app/utils/paths.py -> app/utils -> app -> program
    return Path(__file__).resolve().parents[2]


def resource_dir() -> Path:
    """Carpeta de recursos por defecto (ícono/fondo/QSS embebidos en el .exe)."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "resources"
    return base_dir() / "resources"


def data_dir() -> Path:
    """Carpeta de datos locales (BD, apariencia personalizada, solicitudes, exportados)."""
    d = base_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "pae.db"


def appearance_dir() -> Path:
    d = data_dir() / "appearance"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reset_requests_dir() -> Path:
    d = data_dir() / "reset_requests"
    d.mkdir(parents=True, exist_ok=True)
    return d


def exports_dir() -> Path:
    d = data_dir() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def update_dir() -> Path:
    """Carpeta para descargas temporales de actualizaciones del programa."""
    d = data_dir() / "update"
    d.mkdir(parents=True, exist_ok=True)
    return d


def updater_exe_path() -> Path:
    """Ruta esperada de updater.exe, distribuido junto a SistemaPAE.exe."""
    return base_dir() / "updater.exe"
