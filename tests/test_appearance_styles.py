from pathlib import Path

from PySide6.QtWidgets import QWidget

from app.db.repositories import settings as settings_repo
from app.ui.widgets.background_widget import BackgroundWidget
from app.ui.widgets.styles import apply_window_background, default_background_path

# La fixture `db` redirige base_dir() a un tmp_path sin carpeta resources/
# (para aislar datos), lo que de paso rompe resource_dir(). Para probar el
# fallback de fábrica necesitamos que siga apuntando a los recursos reales.
_REAL_RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"


def _window_with_background() -> QWidget:
    window = QWidget()
    bg = BackgroundWidget(window)
    window._bg = bg  # mantener referencia
    return window


def test_default_background_path_exists_as_a_bundled_resource():
    assert default_background_path().exists()


def test_never_configured_falls_back_to_factory_background(qapp, db, monkeypatch):
    monkeypatch.setattr("app.ui.widgets.styles.resource_dir", lambda: _REAL_RESOURCES_DIR)

    window = _window_with_background()
    apply_window_background(window)

    bg_widget = window.findChildren(BackgroundWidget)[0]
    assert bg_widget._pixmap is not None


def test_explicit_color_only_choice_is_respected_over_factory_background(qapp, db):
    settings_repo.set(settings_repo.KEY_BACKGROUND_COLOR, "#123456")
    settings_repo.set(settings_repo.KEY_BACKGROUND_PATH, None)

    window = _window_with_background()
    apply_window_background(window)

    bg_widget = window.findChildren(BackgroundWidget)[0]
    assert bg_widget._pixmap is None


def test_explicit_image_choice_is_used_over_factory_background(qapp, db, tmp_path):
    from PySide6.QtGui import QImage

    custom = tmp_path / "custom.png"
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(0xFF0000)
    image.save(str(custom))
    settings_repo.set(settings_repo.KEY_BACKGROUND_PATH, str(custom))

    window = _window_with_background()
    apply_window_background(window)

    bg_widget = window.findChildren(BackgroundWidget)[0]
    assert bg_widget._pixmap is not None
    assert bg_widget._pixmap.width() == 10
