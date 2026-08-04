from unittest.mock import patch

from PySide6.QtWidgets import QDialog

from app.ui.reporteador.asignar_fecha_entrega_dialog import AsignarFechaEntregaDialog
from app.ui.reporteador.assign_lista_dialog import AssignListaDialog


def test_assign_lista_dialog_collects_values_per_file(qapp, db):
    dialog = AssignListaDialog(["origen1.xlsx", "origen2.xlsx"])
    lista_input1, fecha_input1 = dialog._fields["origen1.xlsx"]
    lista_input2, fecha_input2 = dialog._fields["origen2.xlsx"]
    lista_input1.setText("10")
    lista_input2.setText("11")

    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_by_filename["origen1.xlsx"][0] == "10"
    assert dialog.result_by_filename["origen2.xlsx"][0] == "11"
    assert dialog.result_by_filename["origen1.xlsx"][1] == fecha_input1.date().toString("dd/MM/yyyy")


def test_assign_lista_dialog_blocks_accept_when_lista_missing(qapp, db):
    dialog = AssignListaDialog(["origen1.xlsx"])

    with patch("app.ui.reporteador.assign_lista_dialog.QMessageBox.warning") as mock_warn:
        dialog._on_accept()

    mock_warn.assert_called_once()
    assert dialog.result_by_filename == {}
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_asignar_fecha_entrega_dialog_collects_lista_and_fecha(qapp, db):
    dialog = AsignarFechaEntregaDialog(["LISTA-1", "LISTA-2"])
    dialog.lista_combo.setCurrentIndex(1)

    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_lista == "LISTA-2"
    assert dialog.selected_fecha == dialog.fecha_edit.date().toString("dd/MM/yyyy")


def test_asignar_fecha_entrega_dialog_warns_when_no_listas(qapp, db):
    dialog = AsignarFechaEntregaDialog([])

    with patch("app.ui.reporteador.asignar_fecha_entrega_dialog.QMessageBox.warning") as mock_warn:
        dialog._on_accept()

    mock_warn.assert_called_once()
    assert dialog.selected_lista is None
