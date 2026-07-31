from app.config import (
    AUTH_TYPE_CERTIFICADO,
    AUTH_TYPE_PASSWORD,
    ROLE_ABOGADO,
    ROLE_ADMINISTRADOR,
    ROLE_AGENTE_PAE,
    ROLE_SUPERUSUARIO,
)
from app.db.repositories import users as users_repo
from app.ui.main_window import MainWindow


def _tab_titles(window: MainWindow) -> list[str]:
    return [window.tabs.tabText(i) for i in range(window.tabs.count())]


def _make_agente(username="agente1"):
    return users_repo.create_user(
        username=username, role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado(username="abogado1"):
    return users_repo.create_user(
        username=username, role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_admin():
    return users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Administrador", email="c@c.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_super():
    return users_repo.create_user(
        username="super1", role=ROLE_SUPERUSUARIO, full_name="Super Uno", email="s@s.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_agente_starts_on_welcome_only(qapp, db):
    window = MainWindow(_make_agente())
    assert _tab_titles(window) == ["Bienvenida"]


def test_agente_formato_menu_adds_and_reuses_generar_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_generar_formato_tab()
    assert _tab_titles(window) == ["Bienvenida", "Generar Formato Requerimiento"]
    assert window.tabs.currentWidget() is window._formato_widgets["generar_formato"]

    window.tabs.setCurrentIndex(0)
    window._show_generar_formato_tab()
    assert window.tabs.count() == 2  # no se duplica


def test_agente_formato_menu_adds_and_reuses_revisar_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_revisar_formato_tab()
    assert _tab_titles(window) == ["Bienvenida", "Revisar Formato Requerimiento"]
    assert window.tabs.currentWidget() is window._formato_widgets["revisar_formato"]

    window.tabs.setCurrentIndex(0)
    window._show_revisar_formato_tab()
    assert window.tabs.count() == 2  # no se duplica


def test_agente_generar_y_revisar_son_pestanas_independientes(qapp, db):
    window = MainWindow(_make_agente())

    window._show_generar_formato_tab()
    window._show_revisar_formato_tab()

    assert _tab_titles(window) == [
        "Bienvenida", "Generar Formato Requerimiento", "Revisar Formato Requerimiento",
    ]


def test_agente_formato_menu_mandamiento_placeholders(qapp, db):
    window = MainWindow(_make_agente())

    window._show_generar_mandamiento_tab()
    assert "Generar Formato Mandamiento" in _tab_titles(window)
    window._show_generar_mandamiento_tab()
    assert _tab_titles(window).count("Generar Formato Mandamiento") == 1

    window._show_revisar_mandamiento_tab()
    assert "Revisar Formato Mandamiento" in _tab_titles(window)
    window._show_revisar_mandamiento_tab()
    assert _tab_titles(window).count("Revisar Formato Mandamiento") == 1


def test_abogado_formato_menu_mandamientos_placeholder(qapp, db):
    window = MainWindow(_make_abogado())

    window._show_mandamientos_tab()
    assert "Mandamientos (próximamente)" in _tab_titles(window)
    window._show_mandamientos_tab()
    assert _tab_titles(window).count("Mandamientos (próximamente)") == 1


def test_abogado_formato_menu_shows_capture_view(qapp, db):
    window = MainWindow(_make_abogado())

    assert _tab_titles(window) == ["Bienvenida"]
    window._show_requerimientos_tab()
    assert _tab_titles(window)[-1] == "Formato de Requerimientos (Abogado)"


def test_otros_menu_shows_datos_cuenta_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_datos_cuenta_tab()
    assert "Datos de cuenta" in _tab_titles(window)
    window._show_datos_cuenta_tab()
    assert _tab_titles(window).count("Datos de cuenta") == 1


def test_historico_menu_shows_and_reuses_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_historico_tab()
    assert "Histórico" in _tab_titles(window)
    window._show_historico_tab()
    assert _tab_titles(window).count("Histórico") == 1


def test_admin_keeps_direct_requerimientos_tab_plus_welcome(qapp, db):
    window = MainWindow(_make_admin())

    titles = _tab_titles(window)
    assert titles == [
        "Bienvenida",
        "Generar Formato Requerimiento (Agente del PAE)",
        "Revisar Formato Requerimiento (Agente del PAE)",
        "Usuarios",
        "Solicitudes de reset",
        "Apariencia",
        "Datos de cuenta",
        "Trazabilidad",
    ]


def test_permanent_tabs_have_no_close_button(qapp, db):
    window = MainWindow(_make_admin())
    for index in range(window.tabs.count()):
        assert window.tabs.tabBar().tabButton(index, window.tabs.tabBar().ButtonPosition.RightSide) is None


def test_dynamic_tab_can_be_closed_and_reopened(qapp, db):
    window = MainWindow(_make_agente())
    window._show_generar_formato_tab()
    widget = window._formato_widgets["generar_formato"]
    index = window.tabs.indexOf(widget)

    window._on_tab_close_requested(index)

    assert "generar_formato" not in window._formato_widgets
    assert _tab_titles(window) == ["Bienvenida"]

    window._show_generar_formato_tab()
    assert "Generar Formato Requerimiento" in _tab_titles(window)


def test_super_gets_ver_como_menu_and_can_open_agente_simulation(qapp, db):
    agente = _make_agente()
    window = MainWindow(_make_super())

    from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView

    widget = RequerimientosGenerarView(agente, simulate=True)
    window.tabs.addTab(widget, f"Viendo como: {agente.full_name} — Generar Formato Requerimiento")
    window._viendo_como_widgets[f"generar:{agente.id}"] = widget

    assert widget.simulate is True
    assert f"Viendo como: {agente.full_name} — Generar Formato Requerimiento" in _tab_titles(window)


def test_super_can_open_agente_simulation_via_choose_dialog(qapp, db):
    from unittest.mock import MagicMock, patch

    agente = _make_agente()
    window = MainWindow(_make_super())

    mock_dialog = MagicMock()
    from PySide6.QtWidgets import QDialog
    mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog.selected_user = agente

    with patch("app.ui.widgets.choose_user_dialog.ChooseUserDialog", return_value=mock_dialog):
        window._on_choose_view_as()

    titles = _tab_titles(window)
    assert f"Viendo como: {agente.full_name} — Generar Formato Requerimiento" in titles
    assert f"Viendo como: {agente.full_name} — Revisar Formato Requerimiento" in titles
    assert f"generar:{agente.id}" in window._viendo_como_widgets
    assert f"revisar:{agente.id}" in window._viendo_como_widgets
