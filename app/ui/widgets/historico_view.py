"""Histórico local de archivos cargados, para Agente del PAE y Abogado --
lee directamente `imported_files`/`mandamiento_imported_files` de esta misma
máquina (a diferencia de la Trazabilidad del Súper/Admin, que importa el
pae.db de OTRA máquina). Una pestaña por tipo de documento."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import ROLE_AGENTE_PAE
from app.db.repositories import mandamientos as mand_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories.users import User
from app.utils.dates import format_local_datetime

HEADERS_AGENTE = ["Archivo", "Filas", "Abogado", "Fecha y hora"]
HEADERS_ABOGADO = ["Archivo", "Filas", "Agente del PAE", "Fecha y hora"]


def _build_table(headers: list[str], rows, other_key: str) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    for row in rows:
        r = table.rowCount()
        table.insertRow(r)
        filename_item = QTableWidgetItem(row["original_filename"])
        filename_item.setData(Qt.ItemDataRole.UserRole, row["original_path"])
        table.setItem(r, 0, filename_item)
        table.setItem(r, 1, QTableWidgetItem(str(row["row_count"])))
        table.setItem(r, 2, QTableWidgetItem(row[other_key] or ""))
        table.setItem(r, 3, QTableWidgetItem(format_local_datetime(row["imported_at"])))
    return table


class HistoricoView(QWidget):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user
        is_agente = user.role == ROLE_AGENTE_PAE
        headers = HEADERS_AGENTE if is_agente else HEADERS_ABOGADO
        other_key = "abogado_nombre" if is_agente else "agente_nombre"

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Archivos que ha cargado en esta computadora:"))

        if is_agente:
            rows_req = req_repo.list_imported_files_for_agente(user.id)
            rows_mand = mand_repo.list_imported_files_for_agente(user.id)
        else:
            rows_req = req_repo.list_imported_files_for_abogado(user.id)
            rows_mand = mand_repo.list_imported_files_for_abogado(user.id)

        self.table_requerimiento = _build_table(headers, rows_req, other_key)
        self.table_mandamiento = _build_table(headers, rows_mand, other_key)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.table_requerimiento, "Requerimiento")
        self.tabs.addTab(self.table_mandamiento, "Mandamiento")
        layout.addWidget(self.tabs)

        open_location_btn = QPushButton("Abrir ubicación del archivo")
        open_location_btn.clicked.connect(self._on_open_location)
        layout.addWidget(open_location_btn)

    def _on_open_location(self) -> None:
        table = self.tabs.currentWidget()
        selected = table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Ninguna fila seleccionada", "Seleccione primero un archivo de la lista.")
            return

        row = selected[0].row()
        original_path = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not original_path:
            QMessageBox.information(
                self,
                "Ubicación no disponible",
                "No se registró la ubicación de este archivo (se cargó con una versión anterior del programa).",
            )
            return

        path = Path(original_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                f"El archivo ya no se encuentra en esa ubicación:\n\n{path}",
            )
            return

        subprocess.Popen(["explorer", "/select,", str(path)])
