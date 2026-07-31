"""Agente del PAE: selecciona abogado, carga Excel y exporta el formato firmado."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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
from app.excel_io import mcdiep_format
from app.excel_io.duplicates import find_duplicate_filenames
from app.excel_io.requerimientos_export import export_for_abogado
from app.excel_io.requerimientos_import import parse_requerimientos_file
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog
from app.utils.paths import exports_dir

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename(text: str) -> str:
    """Reemplaza caracteres inválidos en nombres de archivo de Windows por '_'."""
    return _INVALID_FILENAME_CHARS.sub("_", text).strip()


class RequerimientosGenerarView(QWidget):
    def __init__(self, agente_user: users_repo.User, parent=None, simulate: bool = False):
        super().__init__(parent)
        self.agente_user = agente_user
        self.simulate = simulate
        self._rows: list[dict] = []
        self._source_filenames: list[str] = []

        layout = QVBoxLayout(self)

        if self.simulate:
            banner = QLabel(
                "Modo simulación: puede probar el flujo completo, pero nada de lo que haga "
                "aquí se guarda."
            )
            banner.setStyleSheet(
                "background-color: rgba(255, 224, 138, 0.9); padding: 6px; border-radius: 4px;"
            )
            layout.addWidget(banner)

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

        self.files_label = QLabel("Archivos en este lote: (ninguno)")
        self.files_label.setWordWrap(True)
        layout.addWidget(self.files_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
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

            if not self.simulate:
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
        if self._source_filenames:
            self.files_label.setText("Archivos en este lote: " + ", ".join(self._source_filenames))
        else:
            self.files_label.setText("Archivos en este lote: (ninguno)")

        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self._rows))
            for r, row in enumerate(self._rows):
                self.table.setItem(r, 0, QTableWidgetItem(row["folio"] or ""))
                self.table.setItem(r, 1, QTableWidgetItem(row["cta_predial"] or ""))
                self.table.setItem(r, 2, QTableWidgetItem(row["contribuyente"] or ""))
                self.table.setItem(r, 3, QTableWidgetItem(row["domicilio"] or ""))
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_export(self) -> None:
        if not self._rows:
            QMessageBox.warning(self, "Nada que exportar", "Seleccione al menos un archivo Excel primero.")
            return

        abogado_id = self.abogado_combo.currentData()
        abogado = users_repo.get_by_id(abogado_id)

        if self.simulate:
            QMessageBox.information(
                self, "Simulación",
                f"Se habrían exportado {len(self._rows)} filas para {abogado.full_name}. "
                "No se guardó ni exportó nada de verdad.",
            )
        else:
            proceed = QMessageBox.question(
                self, "Confirmar exportación",
                f"Se exportarán {len(self._rows)} filas para {abogado.full_name}, con datos de "
                "los siguientes archivos:\n\n" + "\n".join(self._source_filenames) + "\n\n¿Continuar?",
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

            if not users_repo.has_certificate(self.agente_user):
                QMessageBox.warning(
                    self, "Sin certificado registrado",
                    "Debe tener un certificado generado para poder firmar el archivo que se exporta.",
                )
                return

            confirm_dialog = CertificateConfirmDialog(
                self.agente_user, parent=self,
                message=(
                    "El archivo que se va a exportar para el Abogado queda firmado con su "
                    "certificado. Confirme su identidad con su certificado actual."
                ),
            )
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                return

            fecha = datetime.now().strftime("%d_%m_%Y")
            filename = f"LISTA DEL {fecha} {_sanitize_filename(abogado.full_name)}{mcdiep_format.EXTENSION}"
            folder = QFileDialog.getExistingDirectory(
                self, "Elegir carpeta para guardar el archivo exportado", str(exports_dir())
            )
            if not folder:
                return
            output_path = Path(folder) / filename

            if output_path.exists():
                overwrite = QMessageBox.question(
                    self, "El archivo ya existe",
                    f"Ya existe un archivo con ese nombre en la carpeta elegida:\n{output_path.name}"
                    "\n\n¿Reemplazarlo?",
                )
                if overwrite != QMessageBox.StandardButton.Yes:
                    return

            batch_id = req_repo.create_batch(abogado_id=abogado_id, agente_id=self.agente_user.id)
            req_repo.add_rows(batch_id, self._rows)
            req_repo.link_imported_files_to_batch(
                agente_id=self.agente_user.id, filenames=self._source_filenames, batch_id=batch_id
            )

            export_for_abogado(
                self._rows, output_path,
                agente=self.agente_user, abogado=abogado, private_key=confirm_dialog.private_key,
            )
            req_repo.set_batch_export_path(batch_id, agente_path=str(output_path))

            QMessageBox.information(
                self, "Exportado",
                f"Se exportaron y firmaron {len(self._rows)} filas para {abogado.full_name}:\n{output_path}",
            )

        self._rows = []
        self._source_filenames = []
        self._refresh_preview()
