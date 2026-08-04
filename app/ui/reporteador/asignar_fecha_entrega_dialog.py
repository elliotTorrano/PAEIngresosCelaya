"""Diálogo del Reporteador: aplica una misma fecha de entrega a todas las
filas del reporte que compartan un número de LISTA."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.config import window_title
from app.ui.widgets.styles import apply_base_style


class AsignarFechaEntregaDialog(QDialog):
    def __init__(self, lista_numeros: list[str], parent=None):
        super().__init__(parent)
        apply_base_style(self)
        self.setWindowTitle(window_title("Asignar fecha de entrega"))
        self.selected_lista: str | None = None
        self.selected_fecha: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Número de lista:"))
        self.lista_combo = QComboBox()
        for numero in lista_numeros:
            self.lista_combo.addItem(numero, numero)
        layout.addWidget(self.lista_combo)

        layout.addWidget(QLabel("Fecha de entrega:"))
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDisplayFormat("dd/MM/yyyy")
        self.fecha_edit.setDate(QDate.currentDate())
        layout.addWidget(self.fecha_edit)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Aceptar")
        ok_btn.clicked.connect(self._on_accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_accept(self) -> None:
        if self.lista_combo.currentData() is None:
            QMessageBox.warning(self, "Nada que asignar", "No hay ninguna lista disponible todavía.")
            return
        self.selected_lista = self.lista_combo.currentData()
        self.selected_fecha = self.fecha_edit.date().toString("dd/MM/yyyy")
        self.accept()
