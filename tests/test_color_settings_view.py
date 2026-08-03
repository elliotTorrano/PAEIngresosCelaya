from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox, QPushButton

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR
from app.db.repositories import settings as settings_repo
from app.db.repositories import users as users_repo
from app.ui.admin.color_settings_view import ROLE_ORDER, ColorSettingsView
from app.ui.widgets import theme


def _make_admin():
    return users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Admin", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_loads_current_colors_into_fields(qapp, db):
    view = ColorSettingsView(_make_admin())
    for role in ROLE_ORDER:
        assert view._inputs[role].text() == theme.DEFAULT_COLORS[role]


def test_invalid_hex_blocks_apply(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("no-es-un-color")

    with patch("app.ui.admin.color_settings_view.QMessageBox.warning") as mock_warning:
        view._on_apply_preview()

    mock_warning.assert_called_once()
    assert theme.current_colors() == theme.DEFAULT_COLORS


def test_apply_preview_updates_current_colors_without_saving(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("#111111")
    view._inputs["critico"].setText("#222222")
    view._inputs["estructura"].setText("#333333")

    with patch("app.ui.admin.color_settings_view.QMessageBox.information"):
        view._on_apply_preview()

    assert theme.current_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
    assert theme.saved_colors() == theme.DEFAULT_COLORS  # no se guardó todavía


def test_save_interface_requires_confirmation(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("#111111")
    view._inputs["critico"].setText("#222222")
    view._inputs["estructura"].setText("#333333")

    with patch(
        "app.ui.admin.color_settings_view.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.No,
    ):
        view._on_save_interface()

    assert settings_repo.get(settings_repo.KEY_THEME_IDENTITY) is None


def test_save_interface_persists_when_confirmed(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("#111111")
    view._inputs["critico"].setText("#222222")
    view._inputs["estructura"].setText("#333333")

    with patch(
        "app.ui.admin.color_settings_view.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.admin.color_settings_view.QMessageBox.information"):
        view._on_save_interface()

    assert settings_repo.get(settings_repo.KEY_THEME_IDENTITY) == "#111111"
    assert theme.saved_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
    # Guardar interfaz no debe tocar la paleta del PDF.
    assert theme.saved_pdf_colors() == theme.DEFAULT_COLORS


def test_save_pdf_requires_confirmation(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("#111111")
    view._inputs["critico"].setText("#222222")
    view._inputs["estructura"].setText("#333333")

    with patch(
        "app.ui.admin.color_settings_view.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.No,
    ):
        view._on_save_pdf()

    assert settings_repo.get(settings_repo.KEY_PDF_THEME_IDENTITY) is None


def test_save_pdf_persists_when_confirmed(qapp, db):
    view = ColorSettingsView(_make_admin())
    view._inputs["identidad"].setText("#111111")
    view._inputs["critico"].setText("#222222")
    view._inputs["estructura"].setText("#333333")

    with patch(
        "app.ui.admin.color_settings_view.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.admin.color_settings_view.QMessageBox.information"):
        view._on_save_pdf()

    assert settings_repo.get(settings_repo.KEY_PDF_THEME_IDENTITY) == "#111111"
    assert theme.saved_pdf_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
    # Guardar PDF no debe tocar la paleta de interfaz.
    assert theme.saved_colors() == theme.DEFAULT_COLORS
    assert "#222222" in view._pdf_status_label.text()


def test_allow_pdf_false_hides_pdf_controls(qapp, db):
    view = ColorSettingsView(_make_admin(), allow_pdf=False)
    assert not hasattr(view, "_pdf_status_label")

    labels = [btn.text() for btn in view.findChildren(QPushButton)]
    assert "Guardar cambios del PDF" not in labels
    assert "Guardar cambios de interfaz" in labels


def test_reset_defaults_restores_factory_colors_after_custom_save(qapp, db):
    theme.save_as_default({"identidad": "#111111", "critico": "#222222", "estructura": "#333333"})

    view = ColorSettingsView(_make_admin())
    with patch("app.ui.admin.color_settings_view.QMessageBox.information"):
        view._on_reset_defaults()

    for role in ("identidad", "critico", "estructura"):
        assert view._inputs[role].text() == theme.DEFAULT_COLORS[role]
    assert theme.current_colors() == theme.DEFAULT_COLORS
    # Restaurar predeterminados es sólo vista previa -- lo guardado (el
    # personalizado) sigue intacto hasta que se presione "Guardar".
    assert theme.saved_colors() == {"identidad": "#111111", "critico": "#222222", "estructura": "#333333"}
