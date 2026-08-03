"""Histórico local de archivos cargados, para Agente del PAE y Abogado --
lee directamente `imported_files`/`mandamiento_imported_files` de esta misma
máquina (a diferencia de la Trazabilidad del Súper/Admin, que importa el
pae.db de OTRA máquina). Una pestaña por tipo de documento."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
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
    for row in rows:
        r = table.rowCount()
        table.insertRow(r)
        table.setItem(r, 0, QTableWidgetItem(row["original_filename"]))
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

        tabs = QTabWidget()
        tabs.addTab(self.table_requerimiento, "Requerimiento")
        tabs.addTab(self.table_mandamiento, "Mandamiento")
        layout.addWidget(tabs)
