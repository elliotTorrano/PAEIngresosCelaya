"""Agente del PAE: selecciona abogado, carga Excel, revisa duplicados y exporta."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import ROLE_ABOGADO
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.duplicates import find_duplicate_filenames
from app.excel_io.requerimientos_export import export_for_abogado
from app.excel_io.requerimientos_import import parse_requerimientos_file
from app.utils.paths import exports_dir


class RequerimientosImportView(QWidget):
    def __init__(self, agente_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.agente_user = agente_user
        self._rows: list[dict] = []
        self._source_filenames: list[str] = []

        layout = QVBoxLayout(self)

        abogado_row = QHBoxLayout()
        abogado_row.addWidget(QLabel("Abogado asignado:"))
        self.abogado_combo = QComboBox()
        for abogado in users_repo.list_by_role(ROLE_ABOGADO):
            self.abogado_combo.addItem(f"{abogado.full_name} ({abogado.username})", abogado.id)
        abogado_row.addWidget(self.abogado_combo)
        layout.addLayout(abogado_row)

        select_btn = QPushButton("Seleccionar archivos Excel")
        select_btn.clicked.connect(self._on_select_files)
        layout.addWidget(select_btn)

        self.count_label = QLabel("Filas importadas: 0")
        layout.addWidget(self.count_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        export_btn = QPushButton("Exportar para el Abogado")
        export_btn.clicked.connect(self._on_export)
        layout.addWidget(export_btn)

        if self.abogado_combo.count() == 0:
            select_btn.setEnabled(False)
            export_btn.setEnabled(False)
            layout.addWidget(QLabel("No hay Abogados dados de alta todavía."))

    def _on_select_files(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos Excel", "", "Excel (*.xlsx *.xls)")
        if not file_paths:
            return

        paths = [Path(p) for p in file_paths]
        already_in_batch = set(self._source_filenames)
        duplicates = find_duplicate_filenames(paths, already_in_batch=already_in_batch)
        if duplicates:
            proceed = QMessageBox.question(
                self, "Archivos duplicados",
                "Los siguientes archivos están repetidos en esta selección, o ya se habían "
                "agregado a este lote antes de exportar, y se omitirán:\n\n"
                + "\n".join(duplicates) + "\n\n¿Continuar con el resto?",
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        abogado_id = self.abogado_combo.currentData()
        failed: list[str] = []
        empty: list[str] = []

        for path in paths:
            if path.name in duplicates or path.name in already_in_batch:
                continue

            try:
                result = parse_requerimientos_file(path)
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{path.name}: {exc}")
                continue

            if result.row_count == 0:
                empty.append(path.name)
                continue

            self._rows.extend(result.rows)
            self._source_filenames.append(path.name)
            already_in_batch.add(path.name)

            # Histórico permanente de subidas: quién, cuándo y cuántas filas.
            # No se restringe por repetición -- eso sólo aplica al lote en curso.
            req_repo.record_imported_file(
                original_filename=path.name, agente_id=self.agente_user.id, abogado_id=abogado_id,
                row_count=result.row_count,
            )

        self._refresh_preview()

        if failed:
            QMessageBox.critical(
                self,
                "No se pudieron leer algunos archivos",
                "No se pudo abrir el archivo o no tiene un formato de Excel válido (.xlsx). "
                "Si es un archivo .xls antiguo, ábralo en Excel y guárdelo como .xlsx antes "
                "de importarlo.\n\n" + "\n".join(failed),
            )
        if empty:
            QMessageBox.warning(
                self,
                "Sin filas de datos",
                "No se encontraron filas de datos en:\n\n" + "\n".join(empty) + "\n\n"
                "Recuerde que siempre se omiten las primeras 2 filas y la última fila de "
                "cada archivo (encabezados y pie de página). Si su archivo de prueba no "
                "tiene esa forma -- por ejemplo, no tiene una fila final después de los "
                "datos -- la última fila real se descarta por error.",
            )

    def _refresh_preview(self) -> None:
        self.count_label.setText(f"Filas importadas: {len(self._rows)}")
        self.table.setRowCount(0)
        for row in self._rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["folio"] or ""))
            self.table.setItem(r, 1, QTableWidgetItem(row["cta_predial"] or ""))
            self.table.setItem(r, 2, QTableWidgetItem(row["contribuyente"] or ""))
            self.table.setItem(r, 3, QTableWidgetItem(row["domicilio"] or ""))

    def _on_export(self) -> None:
        if not self._rows:
            QMessageBox.warning(self, "Nada que exportar", "Seleccione al menos un archivo Excel primero.")
            return

        abogado_id = self.abogado_combo.currentData()
        abogado = users_repo.get_by_id(abogado_id)

        batch_id = req_repo.create_batch(abogado_id=abogado_id, agente_id=self.agente_user.id)
        req_repo.add_rows(batch_id, self._rows)
        req_repo.link_imported_files_to_batch(
            agente_id=self.agente_user.id, filenames=self._source_filenames, batch_id=batch_id
        )

        output_path = exports_dir() / f"requerimientos_{abogado.username}_lote{batch_id}.xlsx"
        export_for_abogado(self._rows, output_path)
        req_repo.set_batch_export_path(batch_id, agente_path=str(output_path))

        QMessageBox.information(
            self, "Exportado", f"Se exportaron {len(self._rows)} filas para {abogado.full_name}:\n{output_path}"
        )

        self._rows = []
        self._source_filenames = []
        self._refresh_preview()
