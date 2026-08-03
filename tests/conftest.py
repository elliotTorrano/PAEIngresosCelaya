import os
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.db import connection as connection_module
from app.db.migrations import ensure_schema
from app.ui.widgets import theme as theme_module
from app.utils import paths as paths_module

_REAL_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base de datos y carpeta de datos aisladas en un directorio temporal, por
    prueba. Se redirige base_dir() (no sólo db_path) para que exports_dir(),
    appearance_dir(), etc. tampoco escriban dentro del proyecto real.

    resource_dir() = base_dir()/"resources" (fuera de modo congelado/.exe),
    así que redirigir base_dir() también lo desvía a una carpeta sin
    recursos reales -- se copia resources/ real dentro de tmp_path para que
    el escudo/QSS/etc. sigan resolviendo (p. ej. el PDF que ahora se genera
    en las pruebas de exportación, que usa el escudo del login)."""
    monkeypatch.setattr(paths_module, "base_dir", lambda: tmp_path)
    shutil.copytree(_REAL_RESOURCES_DIR, tmp_path / "resources")
    connection_module._connection = None
    ensure_schema()
    theme_module.set_preview_colors(None)
    yield
    connection_module._connection = None
    theme_module.set_preview_colors(None)


@pytest.fixture(scope="session")
def qapp():
    """QApplication headless compartida para pruebas que construyen widgets."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
