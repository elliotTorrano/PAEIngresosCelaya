"""Trazabilidad: el súper-usuario/Administrador importa (sólo lectura) el archivo
pae.db de otra máquina -- un Agente del PAE o un Abogado -- para revisar qué se
hizo ahí y cuándo, sin fusionarlo ni modificar la base propia.

Sólo visible en el menú del súper-usuario y del Administrador (ver main_window.py).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
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

from app.db.repositories import audit as audit_repo
from app.db.repositories.users import User

FILES_HEADERS = ["Archivo", "Filas", "Agente", "Abogado", "Importado (fecha y hora)"]
BATCHES_HEADERS = ["Lote", "Agente", "Abogado", "Estado", "Filas", "Capturadas", "Creado"]


class AuditView(QWidget):
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Importe (sólo para revisión) el archivo pae.db de otra computadora -- por "
                "ejemplo, el de un Agente del PAE o un Abogado -- para ver qué se hizo ahí y "
                "cuándo. Se abre en modo de sólo lectura: no se modifica ni se fusiona con "
                "esta base."
            )
        )

        import_btn = QPushButton("Importar base de datos (.db) para revisar")
        import_btn.clicked.connect(self._on_import)
        layout.addWidget(import_btn)

        self.source_label = QLabel("(ninguna base importada todavía)")
        layout.addWidget(self.source_label)

        self.files_table = QTableWidget(0, len(FILES_HEADERS))
        self.files_table.setHorizontalHeaderLabels(FILES_HEADERS)
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.batches_table = QTableWidget(0, len(BATCHES_HEADERS))
        self.batches_table.setHorizontalHeaderLabels(BATCHES_HEADERS)
        self.batches_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.batches_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        tabs = QTabWidget()
        tabs.addTab(self.files_table, "Archivos importados")
        tabs.addTab(self.batches_table, "Lotes de Requerimientos")
        layout.addWidget(tabs)

    def _on_import(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar pae.db a revisar", "", "Base de datos SQLite (*.db)"
        )
        if not file_path:
            return

        conn = None
        try:
            uri = f"file:{Path(file_path).as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            files = audit_repo.list_imported_files(conn)
            batches = audit_repo.list_batches(conn)
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "No se pudo abrir el archivo", f"¿Es un archivo pae.db válido?\n\n{exc}")
            return
        finally:
            if conn is not None:
                conn.close()

        self.source_label.setText(f"Mostrando (sólo lectura): {file_path}")
        self._fill_files(files)
        self._fill_batches(batches)

    def _fill_files(self, rows: list[sqlite3.Row]) -> None:
        self.files_table.setRowCount(0)
        for row in rows:
            r = self.files_table.rowCount()
            self.files_table.insertRow(r)
            self.files_table.setItem(r, 0, QTableWidgetItem(row["original_filename"]))
            self.files_table.setItem(r, 1, QTableWidgetItem(str(row["row_count"])))
            self.files_table.setItem(r, 2, QTableWidgetItem(row["agente_nombre"] or ""))
            self.files_table.setItem(r, 3, QTableWidgetItem(row["abogado_nombre"] or ""))
            self.files_table.setItem(r, 4, QTableWidgetItem(row["imported_at"] or ""))

    def _fill_batches(self, rows: list[sqlite3.Row]) -> None:
        self.batches_table.setRowCount(0)
        for row in rows:
            r = self.batches_table.rowCount()
            self.batches_table.insertRow(r)
            self.batches_table.setItem(r, 0, QTableWidgetItem(f"#{row['id']}"))
            self.batches_table.setItem(r, 1, QTableWidgetItem(row["agente_nombre"] or ""))
            self.batches_table.setItem(r, 2, QTableWidgetItem(row["abogado_nombre"] or ""))
            self.batches_table.setItem(r, 3, QTableWidgetItem(row["status"]))
            self.batches_table.setItem(r, 4, QTableWidgetItem(str(row["total_filas"])))
            self.batches_table.setItem(r, 5, QTableWidgetItem(str(row["filas_capturadas"])))
            self.batches_table.setItem(r, 6, QTableWidgetItem(row["created_at"] or ""))
