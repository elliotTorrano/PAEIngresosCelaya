"""Pantalla del Reporteador para el reporte general de Mandamientos. Mismo
flujo que app/ui/reporteador/reporte_requerimientos_view.py, sin las
columnas de domicilio (Mandamiento nunca las ha tenido en ningún lado del
programa)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.repositories import reporte_mandamientos as reporte_repo
from app.db.repositories import settings as settings_repo
from app.excel_io.reporte_mandamientos_export import HEADERS, export_reporte_xlsx
from app.excel_io.reporte_mandamientos_import import parse_revision_file, parse_source_file
from app.ui.reporteador.asignar_fecha_entrega_dialog import AsignarFechaEntregaDialog
from app.ui.reporteador.assign_lista_dialog import AssignListaDialog

(
    COL_LISTA, COL_FOLIO, COL_CTA, COL_CONTRIB, COL_ADEUDO, COL_DESPACHO, COL_FECHA_IMPRESO,
    COL_FECHA_ENTREGA, COL_FECHA_RECEPCION, COL_FECHA_CITATORIO, COL_QUIEN_CITATORIO,
    COL_FECHA_DILIGENCIA, COL_CON_QUIEN_NOTIFICO, COL_OBS_ABOGADO, COL_OBS_AREA,
    COL_FECHA_EXTRAJUDICIAL, COL_MOTIVO_SUSPENSION,
) = range(17)

MANUAL_CELLS = (
    (COL_FECHA_RECEPCION, "fecha_recepcion", "dd/mm/aaaa"),
    (COL_OBS_AREA, "observaciones_area", ""),
    (COL_FECHA_EXTRAJUDICIAL, "fecha_extrajudicial", "dd/mm/aaaa"),
    (COL_MOTIVO_SUSPENSION, "motivo_suspension", ""),
)

HIGHLIGHT_COLOR = QColor("#ffe08a")


class ReporteMandamientosView(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self._rows: list[reporte_repo.ReporteMandamientoRow] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Reporte general de Mandamientos: importe primero la(s) lista(s) de origen "
            "(crea las filas por folio) y después la revisión que el Agente exporta al "
            "terminar 'Revisar Formato' (completa despacho y captura del Abogado)."
        ))

        btn_row = QHBoxLayout()
        import_source_btn = QPushButton("Importar lista(s) de origen")
        import_source_btn.clicked.connect(self._on_import_source)
        btn_row.addWidget(import_source_btn)
        import_revision_btn = QPushButton("Importar revisión del Agente")
        import_revision_btn.clicked.connect(self._on_import_revision)
        btn_row.addWidget(import_revision_btn)
        fecha_entrega_btn = QPushButton("Asignar fecha de entrega por lista")
        fecha_entrega_btn.clicked.connect(self._on_asignar_fecha_entrega)
        btn_row.addWidget(fecha_entrega_btn)
        layout.addLayout(btn_row)

        master_row = QHBoxLayout()
        choose_master_btn = QPushButton("Elegir archivo maestro...")
        choose_master_btn.clicked.connect(self._on_choose_master_file)
        master_row.addWidget(choose_master_btn)
        export_copy_btn = QPushButton("Exportar copia...")
        export_copy_btn.setProperty("role", "primary")
        export_copy_btn.clicked.connect(self._on_export_copy)
        master_row.addWidget(export_copy_btn)
        self.master_path_label = QLabel()
        master_row.addWidget(self.master_path_label, 1)
        layout.addLayout(master_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar por FOLIO:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escriba el folio y presione Enter...")
        self.search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self.search_input)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._update_master_path_label()
        self._refresh_table()

    # --- Tabla ---------------------------------------------------------------------
    def _refresh_table(self) -> None:
        self._rows = reporte_repo.list_rows()
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self._rows))
            for r, row in enumerate(self._rows):
                self._fill_row(r, row)
        finally:
            self.table.setUpdatesEnabled(True)

    def _fill_row(self, r: int, row: reporte_repo.ReporteMandamientoRow) -> None:
        manual_cols = {col for col, _field, _placeholder in MANUAL_CELLS}
        values = [
            row.lista_numero, row.folio, row.cta_predial, row.contribuyente, row.adeudo,
            row.despacho, row.fecha_impreso, row.fecha_entrega, row.fecha_recepcion,
            row.fecha_citatorio, row.quien_recibe_citatorio, row.fecha_diligencia,
            row.con_quien_notifico, row.observaciones_abogado, row.observaciones_area,
            row.fecha_extrajudicial, row.motivo_suspension,
        ]
        for col, value in enumerate(values):
            if col in manual_cols:
                continue
            item = QTableWidgetItem(value or "")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, col, item)

        for col, field, placeholder in MANUAL_CELLS:
            edit = QLineEdit(getattr(row, field) or "")
            edit.setPlaceholderText(placeholder)
            edit.editingFinished.connect(
                lambda rid=row.id, f=field, w=edit: self._on_manual_field_changed(rid, f, w)
            )
            self.table.setCellWidget(r, col, edit)

    def _on_manual_field_changed(self, row_id: int, field: str, widget: QLineEdit) -> None:
        value = widget.text().strip() or None
        reporte_repo.update_manual_field(row_id, field, value)
        self._sync_master_file()

    # --- Importar lista(s) de origen ------------------------------------------------
    def _on_import_source(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar lista(s) de origen", "", "Excel (*.xlsx *.xls *.xlsm)"
        )
        if not file_paths:
            return

        parsed = [(Path(p).name, parse_source_file(Path(p))) for p in file_paths]

        dialog = AssignListaDialog([name for name, _result in parsed], parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        total_processed = 0
        total_duplicates: list[str] = []
        for name, result in parsed:
            lista_numero, fecha_impreso = dialog.result_by_filename[name]
            outcome = reporte_repo.add_source_rows(
                result.rows, lista_numero=lista_numero, fecha_impreso=fecha_impreso, source_filename=name,
            )
            total_processed += outcome.processed
            total_duplicates.extend(outcome.duplicates)

        self._refresh_table()
        self._sync_master_file()
        self._show_import_summary(total_processed, total_duplicates)

    # --- Importar revisión del Agente ------------------------------------------------
    def _on_import_revision(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar revisión exportada por el Agente", "", "Excel (*.xlsx)"
        )
        if not file_paths:
            return

        total_processed = 0
        total_duplicates: list[str] = []
        for file_path in file_paths:
            result = parse_revision_file(Path(file_path))
            outcome = reporte_repo.add_revision_rows(result.rows)
            total_processed += outcome.processed
            total_duplicates.extend(outcome.duplicates)

        self._refresh_table()
        self._sync_master_file()
        self._show_import_summary(total_processed, total_duplicates)

    def _show_import_summary(self, processed: int, duplicates: list[str]) -> None:
        message = f"Se agregaron o completaron {processed} folios."
        if duplicates:
            message += (
                f"\n\nSe detectaron {len(duplicates)} folios duplicados (ya estaban en el "
                f"reporte, no se modificaron): {', '.join(duplicates)}"
            )
        QMessageBox.information(self, "Importado", message)

    # --- Asignar fecha de entrega ------------------------------------------------------
    def _on_asignar_fecha_entrega(self) -> None:
        listas = sorted({row.lista_numero for row in self._rows if row.lista_numero})
        if not listas:
            QMessageBox.information(
                self, "Nada que asignar", "No hay ninguna lista importada todavía."
            )
            return

        dialog = AsignarFechaEntregaDialog(listas, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated = reporte_repo.bulk_set_fecha_entrega(dialog.selected_lista, dialog.selected_fecha)
        self._refresh_table()
        self._sync_master_file()
        QMessageBox.information(
            self, "Fecha de entrega asignada",
            f"Se actualizaron {updated} filas de la lista {dialog.selected_lista}.",
        )

    # --- Archivo maestro / exportación manual ------------------------------------------
    def _update_master_path_label(self) -> None:
        path = settings_repo.get(settings_repo.KEY_REPORTE_MANDAMIENTOS_EXCEL_PATH)
        self.master_path_label.setText(f"Archivo maestro: {path}" if path else "Archivo maestro: (ninguno elegido)")

    def _on_choose_master_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Elegir archivo maestro del reporte", "Reporte General Mandamientos.xlsx", "Excel (*.xlsx)"
        )
        if not file_path:
            return
        settings_repo.set(settings_repo.KEY_REPORTE_MANDAMIENTOS_EXCEL_PATH, file_path)
        self._update_master_path_label()
        self._sync_master_file()

    def _sync_master_file(self) -> None:
        path = settings_repo.get(settings_repo.KEY_REPORTE_MANDAMIENTOS_EXCEL_PATH)
        if not path:
            return
        try:
            export_reporte_xlsx(reporte_repo.list_rows(), Path(path))
        except OSError as exc:
            QMessageBox.warning(
                self, "No se pudo actualizar el archivo maestro",
                f"El reporte se guardó en la base de datos, pero no se pudo escribir el "
                f"archivo maestro (¿está abierto en Excel?):\n{path}\n\n{exc}",
            )

    def _on_export_copy(self) -> None:
        if not self._rows:
            QMessageBox.warning(self, "Nada que exportar", "El reporte no tiene filas todavía.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar copia del reporte", "Reporte General Mandamientos.xlsx", "Excel (*.xlsx)"
        )
        if not file_path:
            return
        export_reporte_xlsx(self._rows, Path(file_path))
        QMessageBox.information(self, "Exportado", f"Copia exportada:\n{file_path}")

    # --- Buscar --------------------------------------------------------------------------
    def _on_search(self) -> None:
        text = self.search_input.text().strip().lower()
        if not text:
            return
        for row_index, row in enumerate(self._rows):
            if row.folio and text in row.folio.lower():
                self.table.scrollToItem(self.table.item(row_index, COL_FOLIO))
                self.table.selectRow(row_index)
                self._flash_highlight(row_index)
                return
        QMessageBox.information(self, "Sin resultados", "No se encontró ningún folio que coincida con la búsqueda.")

    def _flash_highlight(self, row_index: int) -> None:
        item = self.table.item(row_index, COL_FOLIO)
        if item is None:
            return
        original = item.background()
        item.setBackground(HIGHLIGHT_COLOR)

        def revert():
            current = self.table.item(row_index, COL_FOLIO)
            if current is not None:
                current.setBackground(original)

        QTimer.singleShot(1000, revert)
