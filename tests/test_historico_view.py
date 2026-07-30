from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.ui.widgets.historico_view import HistoricoView


def _make_agente(username="agente1", full_name="Agente Uno"):
    return users_repo.create_user(
        username=username, role=ROLE_AGENTE_PAE, full_name=full_name, email=f"{username}@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado(username="abogado1", full_name="Abogado Uno"):
    return users_repo.create_user(
        username=username, role=ROLE_ABOGADO, full_name=full_name, email=f"{username}@a.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def test_historico_view_shows_only_agente_own_files(qapp, db):
    agente1 = _make_agente()
    agente2 = _make_agente(username="agente2", full_name="Agente Dos")
    abogado = _make_abogado()

    req_repo.record_imported_file(
        original_filename="mio.xlsx", agente_id=agente1.id, abogado_id=abogado.id, row_count=3
    )
    req_repo.record_imported_file(
        original_filename="ajeno.xlsx", agente_id=agente2.id, abogado_id=abogado.id, row_count=5
    )

    view = HistoricoView(agente1)

    assert view.table.rowCount() == 1
    assert view.table.item(0, 0).text() == "mio.xlsx"
    assert view.table.item(0, 2).text() == "Abogado Uno"


def test_historico_view_shows_only_abogado_own_files(qapp, db):
    agente = _make_agente()
    abogado1 = _make_abogado()
    abogado2 = _make_abogado(username="abogado2", full_name="Abogado Dos")

    req_repo.record_imported_file(
        original_filename="mio.xlsx", agente_id=agente.id, abogado_id=abogado1.id, row_count=3
    )
    req_repo.record_imported_file(
        original_filename="ajeno.xlsx", agente_id=agente.id, abogado_id=abogado2.id, row_count=5
    )

    view = HistoricoView(abogado1)

    assert view.table.rowCount() == 1
    assert view.table.item(0, 0).text() == "mio.xlsx"
    assert view.table.item(0, 2).text() == "Agente Uno"
