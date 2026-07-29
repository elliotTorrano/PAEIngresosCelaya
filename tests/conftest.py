import pytest

from app.db import connection as connection_module
from app.db.migrations import ensure_schema


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base de datos SQLite aislada en un archivo temporal, por prueba."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(connection_module, "db_path", lambda: db_file)
    connection_module._connection = None
    ensure_schema()
    yield
    connection_module._connection = None
