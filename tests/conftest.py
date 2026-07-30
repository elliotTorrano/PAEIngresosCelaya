import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.db import connection as connection_module
from app.db.migrations import ensure_schema
from app.utils import paths as paths_module


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base de datos y carpeta de datos aisladas en un directorio temporal, por
    prueba. Se redirige base_dir() (no sólo db_path) para que exports_dir(),
    appearance_dir(), etc. tampoco escriban dentro del proyecto real."""
    monkeypatch.setattr(paths_module, "base_dir", lambda: tmp_path)
    connection_module._connection = None
    ensure_schema()
    yield
    connection_module._connection = None


@pytest.fixture(scope="session")
def qapp():
    """QApplication headless compartida para pruebas que construyen widgets."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
