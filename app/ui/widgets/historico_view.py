"""Histórico local de archivos cargados, para Agente del PAE y Abogado --
lee directamente `imported_files` de esta misma máquina (a diferencia de la
Trazabilidad del Súper/Admin, que importa el pae.db de OTRA máquina)."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.config import ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories.users import User
from app.utils.dates import format_local_datetime

HEADERS_AGENTE = ["Archivo", "Filas", "Abogado", "Fecha y hora"]
HEADERS_ABOGADO = ["Archivo", "Filas", "Agente del PAE", "Fecha y hora"]


class HistoricoView(QWidget):
    def __init__(self, user: User, parent=None):
        super().__init__(parent)
        self.user = user
        is_agente = user.role == ROLE_AGENTE_PAE
        headers = HEADERS_AGENTE if is_agente else HEADERS_ABOGADO

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Archivos que ha cargado en esta computadora:"))

        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        if is_agente:
            rows = req_repo.list_imported_files_for_agente(user.id)
            other_key = "abogado_nombre"
        else:
            rows = req_repo.list_imported_files_for_abogado(user.id)
            other_key = "agente_nombre"

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["original_filename"]))
            self.table.setItem(r, 1, QTableWidgetItem(str(row["row_count"])))
            self.table.setItem(r, 2, QTableWidgetItem(row[other_key] or ""))
            self.table.setItem(r, 3, QTableWidgetItem(format_local_datetime(row["imported_at"])))
