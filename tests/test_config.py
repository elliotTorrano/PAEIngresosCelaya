from app.__version__ import __version__
from app.config import window_title


def test_window_title_format():
    assert window_title("Iniciar sesión") == f"Iniciar sesión - SICPAE v{__version__}"
