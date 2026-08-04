"""Diálogo del Reporteador: tras cargar una o varias listas de origen,
captura a mano el número de LISTA y la fecha de impresión de cada archivo --
ninguno de los dos viaja automáticamente por ningún archivo del programa,
así que se piden aquí, uno junto al nombre del libro que se cargó."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.config import window_title
from app.ui.widgets.styles import apply_base_style


class AssignListaDialog(QDialog):
    def __init__(self, filenames: list[str], parent=None):
        super().__init__(parent)
        apply_base_style(self)
        self.setWindowTitle(window_title("Asignar número de lista"))
        self.result_by_filename: dict[str, tuple[str, str]] = {}
        self._fields: dict[str, tuple[QLineEdit, QDateEdit]] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Capture el número de LISTA y la fecha en que se imprimió cada "
            "archivo cargado:"
        ))

        for filename in filenames:
            row = QHBoxLayout()
            row.addWidget(QLabel(filename), 1)
            lista_input = QLineEdit()
            lista_input.setPlaceholderText("Núm. de lista")
            row.addWidget(lista_input)
            fecha_input = QDateEdit()
            fecha_input.setCalendarPopup(True)
            fecha_input.setDisplayFormat("dd/MM/yyyy")
            fecha_input.setDate(QDate.currentDate())
            row.addWidget(fecha_input)
            layout.addLayout(row)
            self._fields[filename] = (lista_input, fecha_input)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Aceptar")
        ok_btn.clicked.connect(self._on_accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_accept(self) -> None:
        for filename, (lista_input, _fecha_input) in self._fields.items():
            if not lista_input.text().strip():
                QMessageBox.warning(
                    self, "Falta el número de lista",
                    f"Capture el número de lista para '{filename}' antes de continuar.",
                )
                return

        self.result_by_filename = {
            filename: (lista_input.text().strip(), fecha_input.date().toString("dd/MM/yyyy"))
            for filename, (lista_input, fecha_input) in self._fields.items()
        }
        self.accept()
