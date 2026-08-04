from unittest.mock import patch

from PySide6.QtCore import Qt

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import mandamientos as mand_repo
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

    assert view.table_requerimiento.rowCount() == 1
    assert view.table_requerimiento.item(0, 0).text() == "mio.xlsx"
    assert view.table_requerimiento.item(0, 2).text() == "Abogado Uno"


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

    assert view.table_requerimiento.rowCount() == 1
    assert view.table_requerimiento.item(0, 0).text() == "mio.xlsx"
    assert view.table_requerimiento.item(0, 2).text() == "Agente Uno"


def test_historico_view_shows_mandamiento_tab_separately(qapp, db):
    agente = _make_agente()
    abogado = _make_abogado()

    req_repo.record_imported_file(
        original_filename="requerimiento.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=1
    )
    mand_repo.record_imported_file(
        original_filename="mandamiento.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=2
    )

    view = HistoricoView(agente)

    assert view.table_requerimiento.rowCount() == 1
    assert view.table_requerimiento.item(0, 0).text() == "requerimiento.xlsx"
    assert view.table_mandamiento.rowCount() == 1
    assert view.table_mandamiento.item(0, 0).text() == "mandamiento.xlsx"


def test_historico_view_open_location_launches_explorer_when_file_exists(qapp, db, tmp_path):
    agente = _make_agente()
    abogado = _make_abogado()
    source = tmp_path / "lote.xlsx"
    source.write_text("x")

    req_repo.record_imported_file(
        original_filename="lote.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=1,
        original_path=str(source),
    )

    view = HistoricoView(agente)
    view.tabs.setCurrentWidget(view.table_requerimiento)
    view.table_requerimiento.selectRow(0)

    with patch("app.ui.widgets.historico_view.subprocess.Popen") as mock_popen:
        view._on_open_location()

    mock_popen.assert_called_once_with(["explorer", "/select,", str(source)])


def test_historico_view_open_location_warns_when_file_missing(qapp, db, tmp_path):
    agente = _make_agente()
    abogado = _make_abogado()
    missing_path = str(tmp_path / "ya_no_existe.xlsx")

    req_repo.record_imported_file(
        original_filename="ya_no_existe.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=1,
        original_path=missing_path,
    )

    view = HistoricoView(agente)
    view.tabs.setCurrentWidget(view.table_requerimiento)
    view.table_requerimiento.selectRow(0)

    with patch("app.ui.widgets.historico_view.subprocess.Popen") as mock_popen, \
         patch("app.ui.widgets.historico_view.QMessageBox.warning") as mock_warning:
        view._on_open_location()

    mock_popen.assert_not_called()
    mock_warning.assert_called_once()


def test_historico_view_open_location_informs_when_path_not_recorded(qapp, db):
    agente = _make_agente()
    abogado = _make_abogado()

    req_repo.record_imported_file(
        original_filename="viejo.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=1,
    )

    view = HistoricoView(agente)
    view.tabs.setCurrentWidget(view.table_requerimiento)
    view.table_requerimiento.selectRow(0)

    assert view.table_requerimiento.item(0, 0).data(Qt.ItemDataRole.UserRole) is None

    with patch("app.ui.widgets.historico_view.subprocess.Popen") as mock_popen, \
         patch("app.ui.widgets.historico_view.QMessageBox.information") as mock_info:
        view._on_open_location()

    mock_popen.assert_not_called()
    mock_info.assert_called_once()


def test_historico_view_open_location_informs_when_no_selection(qapp, db):
    agente = _make_agente()
    view = HistoricoView(agente)
    view.tabs.setCurrentWidget(view.table_requerimiento)

    with patch("app.ui.widgets.historico_view.subprocess.Popen") as mock_popen, \
         patch("app.ui.widgets.historico_view.QMessageBox.information") as mock_info:
        view._on_open_location()

    mock_popen.assert_not_called()
    mock_info.assert_called_once()
