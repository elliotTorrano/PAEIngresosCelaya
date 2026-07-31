from unittest.mock import patch

import openpyxl

from app.config import AUTH_TYPE_PASSWORD, ROLE_ABOGADO
from app.db.repositories import users as users_repo
from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView


def _make_abogado():
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _write_small_file_without_footer(path):
    """Archivo 'de prueba' típico: título + encabezado + 1 fila de datos, SIN fila
    final de totales -- el caso que confundió al usuario (0 filas, sin aviso)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título de prueba"])
    ws.append(["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"])
    ws.append(["F-001", "CP-001", "Juan Pérez", "Calle 1"])
    wb.save(path)


def test_import_with_no_footer_row_warns_instead_of_silent_zero(qapp, db, tmp_path):
    _make_abogado()
    path = tmp_path / "prueba_sin_pie.xlsx"
    _write_small_file_without_footer(path)

    view = RequerimientosGenerarView(_agente())

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(path)], ""),
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.warning") as mock_warning:
        view._on_select_files()

    assert view._rows == []
    mock_warning.assert_called_once()
    args = mock_warning.call_args[0]
    assert "Sin filas de datos" in args[1]
    assert path.name in args[2]


def test_import_unreadable_file_shows_error_instead_of_crashing(qapp, db, tmp_path):
    _make_abogado()
    bad_path = tmp_path / "no_es_excel.xlsx"
    bad_path.write_text("esto no es un archivo de Excel", encoding="utf-8")

    view = RequerimientosGenerarView(_agente())

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(bad_path)], ""),
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.critical") as mock_critical:
        view._on_select_files()

    assert view._rows == []
    mock_critical.assert_called_once()


def _agente():
    from app.config import AUTH_TYPE_CERTIFICADO, ROLE_AGENTE_PAE

    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
