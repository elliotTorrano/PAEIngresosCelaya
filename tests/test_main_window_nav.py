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


def test_agente_formato_menu_adds_and_reuses_requerimientos_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_requerimientos_tab()
    assert _tab_titles(window) == ["Bienvenida", "Formato de Requerimientos (Agente del PAE)"]
    assert window.tabs.currentWidget() is window._formato_widgets["requerimientos"]

    window.tabs.setCurrentIndex(0)
    window._show_requerimientos_tab()
    assert window.tabs.count() == 2  # no se duplica


def test_agente_formato_menu_mandamientos_placeholder(qapp, db):
    window = MainWindow(_make_agente())

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


def test_admin_keeps_direct_requerimientos_tab_plus_welcome(qapp, db):
    window = MainWindow(_make_admin())

    titles = _tab_titles(window)
    assert titles == [
        "Bienvenida",
        "Formato de Requerimientos (Agente del PAE)",
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
    window._show_requerimientos_tab()
    widget = window._formato_widgets["requerimientos"]
    index = window.tabs.indexOf(widget)

    window._on_tab_close_requested(index)

    assert "requerimientos" not in window._formato_widgets
    assert _tab_titles(window) == ["Bienvenida"]

    window._show_requerimientos_tab()
    assert "Formato de Requerimientos (Agente del PAE)" in _tab_titles(window)


def test_super_gets_ver_como_menu_and_can_open_agente_simulation(qapp, db):
    agente = _make_agente()
    window = MainWindow(_make_super())

    from app.ui.agente.requerimientos_import_view import RequerimientosImportView

    widget = RequerimientosImportView(agente, simulate=True)
    window.tabs.addTab(widget, f"Viendo como: {agente.full_name}")
    window._viendo_como_widgets[agente.id] = widget

    assert widget.simulate is True
    assert f"Viendo como: {agente.full_name}" in _tab_titles(window)
