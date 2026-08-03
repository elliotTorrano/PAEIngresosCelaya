from app.db.repositories import settings as settings_repo
from app.ui.widgets import theme


def test_is_valid_hex():
    assert theme.is_valid_hex("#3A6B46")
    assert theme.is_valid_hex("#abcdef")
    assert not theme.is_valid_hex("3A6B46")
    assert not theme.is_valid_hex("#3A6B4")
    assert not theme.is_valid_hex("#GGGGGG")
    assert not theme.is_valid_hex("")


def test_saved_colors_falls_back_to_defaults_when_nothing_stored(db):
    assert theme.saved_colors() == theme.DEFAULT_COLORS


def test_save_as_default_persists_and_clears_preview(db):
    theme.set_preview_colors({"identidad": "#111111", "critico": "#222222", "estructura": "#333333"})
    assert theme.current_colors()["identidad"] == "#111111"

    theme.save_as_default({"identidad": "#111111", "critico": "#222222", "estructura": "#333333"})

    assert theme.saved_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
    # Guardar como predeterminado apaga cualquier vista previa: lo guardado y
    # lo mostrado deben ser lo mismo de inmediato.
    assert theme.current_colors() == theme.saved_colors()
    assert settings_repo.get(settings_repo.KEY_THEME_IDENTITY) == "#111111"


def test_preview_overrides_saved_without_persisting(db):
    theme.save_as_default(dict(theme.DEFAULT_COLORS))
    theme.set_preview_colors({"identidad": "#ABCDEF", "critico": "#8A1E2D", "estructura": "#A67242"})

    assert theme.current_colors()["identidad"] == "#ABCDEF"
    assert theme.saved_colors()["identidad"] == theme.DEFAULT_COLORS["identidad"]

    theme.set_preview_colors(None)
    assert theme.current_colors() == theme.saved_colors()


def test_render_qss_substitutes_all_placeholders(db):
    theme.set_preview_colors(None)
    qss = theme.render_qss()
    assert "$" not in qss
    assert "#3A6B46" in qss  # color de identidad de fábrica presente tal cual
    assert "#8A1E2D" in qss  # color crítico de fábrica presente tal cual


def test_render_qss_reflects_custom_colors(db):
    theme.set_preview_colors({"identidad": "#123456", "critico": "#654321", "estructura": "#ABCDEF"})
    qss = theme.render_qss()
    assert "#123456" in qss
    assert "#654321" in qss
    theme.set_preview_colors(None)


def test_saved_pdf_colors_falls_back_to_defaults_when_nothing_stored(db):
    assert theme.saved_pdf_colors() == theme.DEFAULT_COLORS


def test_save_pdf_colors_persists_independently_of_interface(db):
    theme.save_as_default({"identidad": "#111111", "critico": "#222222", "estructura": "#333333"})
    theme.save_pdf_colors({"identidad": "#AAAAAA", "critico": "#BBBBBB", "estructura": "#CCCCCC"})

    assert theme.saved_pdf_colors() == {"identidad": "#AAAAAA", "critico": "#BBBBBB", "estructura": "#CCCCCC"}
    # Guardar el PDF no debe tocar la paleta de interfaz, ni viceversa.
    assert theme.saved_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
    assert settings_repo.get(settings_repo.KEY_PDF_THEME_CRITICAL) == "#BBBBBB"
    assert settings_repo.get(settings_repo.KEY_THEME_CRITICAL) == "#222222"


def test_save_as_default_does_not_touch_pdf_colors(db):
    theme.save_pdf_colors({"identidad": "#AAAAAA", "critico": "#BBBBBB", "estructura": "#CCCCCC"})
    theme.save_as_default({"identidad": "#111111", "critico": "#222222", "estructura": "#333333"})

    assert theme.saved_pdf_colors() == {"identidad": "#AAAAAA", "critico": "#BBBBBB", "estructura": "#CCCCCC"}
