from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_ADMINISTRADOR, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.ui.main_window import MainWindow


def _tab_titles(window: MainWindow) -> list[str]:
    return [window.tabs.tabText(i) for i in range(window.tabs.count())]


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado():
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_admin():
    return users_repo.create_user(
        username="admin", role=ROLE_ADMINISTRADOR, full_name="Administrador", email="c@c.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_agente_starts_on_welcome_and_account_without_requerimientos_tab(qapp, db):
    window = MainWindow(_make_agente())

    titles = _tab_titles(window)
    assert titles == ["Bienvenida", "Datos de cuenta"]


def test_agente_formato_menu_adds_and_reuses_requerimientos_tab(qapp, db):
    window = MainWindow(_make_agente())

    window._show_requerimientos_tab()
    assert _tab_titles(window) == ["Bienvenida", "Datos de cuenta", "Formato de Requerimientos (Agente del PAE)"]
    assert window.tabs.currentIndex() == 2

    window.tabs.setCurrentIndex(0)
    window._show_requerimientos_tab()
    assert window.tabs.count() == 3  # no se duplica
    assert window.tabs.currentIndex() == 2


def test_agente_formato_menu_mandamientos_placeholder(qapp, db):
    window = MainWindow(_make_agente())

    window._show_mandamientos_tab()
    assert "Mandamientos (próximamente)" in _tab_titles(window)
    window._show_mandamientos_tab()
    assert _tab_titles(window).count("Mandamientos (próximamente)") == 1


def test_abogado_formato_menu_shows_capture_view(qapp, db):
    window = MainWindow(_make_abogado())

    assert _tab_titles(window) == ["Bienvenida", "Datos de cuenta"]
    window._show_requerimientos_tab()
    assert _tab_titles(window)[-1] == "Formato de Requerimientos (Abogado)"


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
