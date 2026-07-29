"""Abogado: importa el archivo del Agente del PAE, captura el citatorio y exporta.

El Abogado nunca edita FOLIO/CTA PREDIAL/CONTRIBUYENTE/DOMICILIO (se muestran de
sólo lectura); únicamente captura "Fecha de Notificación de citatorio" y
"Quién recibe el citatorio".
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import BATCH_STATUS_EXPORTADO, QUIEN_RECIBE_EN_PUERTA, QUIEN_RECIBE_NOMBRE, ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.requerimientos_export import export_captured
from app.excel_io.requerimientos_import import parse_agente_export_file
from app.utils.paths import exports_dir

COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM, COL_FECHA, COL_QUIEN, COL_NOMBRE = range(7)
HEADERS = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO", "Fecha de notificación", "Quién recibe", "Nombre"]

HIGHLIGHT_COLOR = QColor("#ffe08a")


class RequerimientosCaptureView(QWidget):
    def __init__(self, abogado_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.abogado_user = abogado_user
        self._current_batch_id: int | None = None
        self._rows: list[req_repo.RequerimientoRow] = []

        layout = QVBoxLayout(self)

        import_row = QHBoxLayout()
        import_btn = QPushButton("Importar archivo del Agente del PAE")
        import_btn.clicked.connect(self._on_import)
        import_row.addWidget(import_btn)
        highlight_btn = QPushButton("Resaltar fila faltante de captura")
        highlight_btn.clicked.connect(self._on_highlight_missing)
        import_row.addWidget(highlight_btn)
        export_btn = QPushButton("Exportar")
        export_btn.clicked.connect(self._on_export)
        import_row.addWidget(export_btn)
        layout.addLayout(import_row)

        splitter = QSplitter()
        self.batch_list = QListWidget()
        self.batch_list.setMaximumWidth(260)
        self.batch_list.currentItemChanged.connect(self._on_batch_selected)
        splitter.addWidget(self.batch_list)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        splitter.addWidget(self.table)
        layout.addWidget(splitter)

        self._refresh_batch_list()

    # --- Lotes -------------------------------------------------------------------
    def _refresh_batch_list(self) -> None:
        self.batch_list.clear()
        for batch in req_repo.list_batches_for_abogado(self.abogado_user.id):
            item = QListWidgetItem(f"Lote #{batch['id']} — {batch['status']} — {batch['created_at']}")
            item.setData(1000, batch["id"])
            self.batch_list.addItem(item)

    def _on_batch_selected(self, current: QListWidgetItem, _previous) -> None:
        if current is None:
            return
        self._load_batch(current.data(1000))

    def _load_batch(self, batch_id: int) -> None:
        self._current_batch_id = batch_id
        self._rows = req_repo.list_rows(batch_id)
        self._refresh_table()

    # --- Importar ------------------------------------------------------------------
    def _on_import(self) -> None:
        agentes = users_repo.list_by_role(ROLE_AGENTE_PAE)
        if not agentes:
            QMessageBox.warning(self, "Sin agentes", "No hay Agentes del PAE registrados en esta instalación.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo del Agente del PAE", "", "Excel (*.xlsx)")
        if not file_path:
            return

        agente = agentes[0]
        if len(agentes) > 1:
            from PySide6.QtWidgets import QInputDialog

            labels = [f"{a.full_name} ({a.username})" for a in agentes]
            label, ok = QInputDialog.getItem(self, "Agente", "¿De qué Agente del PAE es este archivo?", labels, editable=False)
            if not ok:
                return
            agente = agentes[labels.index(label)]

        try:
            rows = parse_agente_export_file(Path(file_path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if not rows:
            QMessageBox.warning(self, "Archivo vacío", "No se encontraron filas de datos en el archivo.")
            return

        batch_id = req_repo.create_batch(abogado_id=self.abogado_user.id, agente_id=agente.id)
        req_repo.add_rows(batch_id, rows)
        self._refresh_batch_list()
        self._load_batch(batch_id)
        QMessageBox.information(self, "Importado", f"Se importaron {len(rows)} filas al lote #{batch_id}.")

    # --- Tabla de captura ------------------------------------------------------------
    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        for row in self._rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, COL_FOLIO, QTableWidgetItem(row.folio or ""))
            self.table.setItem(r, COL_CTA, QTableWidgetItem(row.cta_predial or ""))
            self.table.setItem(r, COL_CONTRIB, QTableWidgetItem(row.contribuyente or ""))
            self.table.setItem(r, COL_DOM, QTableWidgetItem(row.domicilio or ""))

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd/MM/yyyy")
            if row.fecha_notificacion:
                date_edit.setDate(QDate.fromString(row.fecha_notificacion, "dd/MM/yyyy"))
            else:
                date_edit.setDate(QDate.currentDate())
            date_edit.dateChanged.connect(lambda _d, row_id=row.id: self._save_row(row_id))
            self.table.setCellWidget(r, COL_FECHA, date_edit)

            quien_combo = QComboBox()
            quien_combo.addItem("", "")
            quien_combo.addItem(QUIEN_RECIBE_EN_PUERTA, QUIEN_RECIBE_EN_PUERTA)
            quien_combo.addItem(QUIEN_RECIBE_NOMBRE, QUIEN_RECIBE_NOMBRE)
            if row.quien_recibe:
                quien_combo.setCurrentIndex(quien_combo.findData(row.quien_recibe))
            self.table.setCellWidget(r, COL_QUIEN, quien_combo)

            nombre_edit = QLineEdit(row.quien_recibe_nombre or "")
            nombre_edit.setEnabled(row.quien_recibe == QUIEN_RECIBE_NOMBRE)
            self.table.setCellWidget(r, COL_NOMBRE, nombre_edit)

            quien_combo.currentIndexChanged.connect(
                lambda _i, row_id=row.id, combo=quien_combo, name_edit=nombre_edit: self._on_quien_changed(
                    row_id, combo, name_edit
                )
            )
            nombre_edit.textChanged.connect(lambda text, row_id=row.id, edit=nombre_edit: self._on_nombre_changed(row_id, text, edit))

    def _on_quien_changed(self, row_id: int, combo: QComboBox, name_edit: QLineEdit) -> None:
        value = combo.currentData()
        name_edit.setEnabled(value == QUIEN_RECIBE_NOMBRE)
        if value != QUIEN_RECIBE_NOMBRE:
            name_edit.clear()
        self._save_row(row_id)

    def _on_nombre_changed(self, row_id: int, text: str, edit: QLineEdit) -> None:
        upper = text.upper()
        if upper != text:
            cursor_pos = edit.cursorPosition()
            edit.blockSignals(True)
            edit.setText(upper)
            edit.setCursorPosition(cursor_pos)
            edit.blockSignals(False)
        self._save_row(row_id)

    def _save_row(self, row_id: int) -> None:
        table_row = self._table_row_for_id(row_id)
        if table_row is None:
            return

        date_edit: QDateEdit = self.table.cellWidget(table_row, COL_FECHA)
        quien_combo: QComboBox = self.table.cellWidget(table_row, COL_QUIEN)
        nombre_edit: QLineEdit = self.table.cellWidget(table_row, COL_NOMBRE)

        quien_value = quien_combo.currentData() or None
        fecha_value = date_edit.date().toString("dd/MM/yyyy") if quien_value else None

        req_repo.update_row_capture(
            row_id,
            fecha_notificacion=fecha_value,
            quien_recibe=quien_value,
            quien_recibe_nombre=nombre_edit.text().strip() or None if quien_value == QUIEN_RECIBE_NOMBRE else None,
        )
        for row in self._rows:
            if row.id == row_id:
                row.fecha_notificacion = fecha_value
                row.quien_recibe = quien_value
                row.quien_recibe_nombre = nombre_edit.text().strip() or None
                break

    def _table_row_for_id(self, row_id: int) -> int | None:
        for idx, row in enumerate(self._rows):
            if row.id == row_id:
                return idx
        return None

    # --- Resaltar faltantes -----------------------------------------------------------
    def _on_highlight_missing(self) -> None:
        missing_index = next((i for i, row in enumerate(self._rows) if not row.is_captured), None)
        if missing_index is None:
            QMessageBox.information(self, "Captura completa", "No hay filas pendientes de captura en este lote.")
            return

        self.table.scrollToItem(self.table.item(missing_index, COL_FOLIO))
        self.table.selectRow(missing_index)

        original_colors = []
        for col in (COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM):
            item = self.table.item(missing_index, col)
            original_colors.append(item.background())
            item.setBackground(HIGHLIGHT_COLOR)

        def revert():
            for col, color in zip((COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM), original_colors):
                item = self.table.item(missing_index, col)
                if item is not None:
                    item.setBackground(color)

        QTimer.singleShot(1000, revert)

    # --- Exportar ------------------------------------------------------------------------
    def _on_export(self) -> None:
        if self._current_batch_id is None or not self._rows:
            QMessageBox.warning(self, "Nada que exportar", "Seleccione un lote con filas capturadas.")
            return

        output_path = exports_dir() / f"requerimientos_capturado_lote{self._current_batch_id}.xlsx"
        export_captured(self._rows, output_path)
        req_repo.set_batch_export_path(self._current_batch_id, abogado_path=str(output_path))
        req_repo.set_batch_status(self._current_batch_id, BATCH_STATUS_EXPORTADO)
        self._refresh_batch_list()

        QMessageBox.information(self, "Exportado", f"Archivo exportado:\n{output_path}")
