"""Agente del PAE: selecciona abogado, carga Excel, revisa duplicados y exporta."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
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
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.duplicates import find_duplicate_filenames
from app.excel_io.requerimientos_export import HEADERS_REVISION, export_for_abogado, export_revision
from app.excel_io.requerimientos_import import (
    McdiepVerificationError,
    parse_abogado_export_file,
    parse_requerimientos_file,
)
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog
from app.utils.paths import exports_dir

PROCEDE_OPTIONS = ("", "PROCEDE", "NO PROCEDE")

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename(text: str) -> str:
    """Reemplaza caracteres inválidos en nombres de archivo de Windows por '_'."""
    return _INVALID_FILENAME_CHARS.sub("_", text).strip()


class RequerimientosImportView(QWidget):
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

        revision_box = QGroupBox("Revisión de captura del Abogado")
        revision_layout = QVBoxLayout(revision_box)
        revision_layout.addWidget(QLabel(
            "Importe el Excel que el Abogado capturó y exportó, para marcar PROCEDE "
            "o NO PROCEDE en cada fila."
        ))

        import_revision_btn = QPushButton("Importar captura del Abogado")
        import_revision_btn.clicked.connect(self._on_import_revision)
        revision_layout.addWidget(import_revision_btn)

        self.revision_table = QTableWidget(0, len(HEADERS_REVISION))
        self.revision_table.setHorizontalHeaderLabels(HEADERS_REVISION)
        self.revision_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.revision_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        revision_layout.addWidget(self.revision_table)

        export_revision_btn = QPushButton("Exportar revisión")
        export_revision_btn.clicked.connect(self._on_export_revision)
        revision_layout.addWidget(export_revision_btn)

        layout.addWidget(revision_box)

        self._refresh_revision_table()

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

        if self.simulate:
            QMessageBox.information(
                self, "Simulación",
                f"Se habrían exportado {len(self._rows)} filas para {abogado.full_name}. "
                "No se guardó ni exportó nada de verdad.",
            )
        else:
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

            batch_id = req_repo.create_batch(abogado_id=abogado_id, agente_id=self.agente_user.id)
            req_repo.add_rows(batch_id, self._rows)
            req_repo.link_imported_files_to_batch(
                agente_id=self.agente_user.id, filenames=self._source_filenames, batch_id=batch_id
            )

            fecha = datetime.now().strftime("%d_%m_%Y")
            output_path = (
                exports_dir()
                / f"LISTA DEL {fecha} {_sanitize_filename(abogado.full_name)}{mcdiep_format.EXTENSION}"
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

    # --- Revisión de captura del Abogado --------------------------------------------

    def _on_import_revision(self) -> None:
        if self.simulate:
            QMessageBox.information(
                self, "No disponible en simulación",
                "En modo simulación no se puede importar ni guardar una revisión nueva.",
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar captura del Abogado", "", "Sistema PAE (*.mcdiep)"
        )
        if not file_path:
            return

        try:
            rows = parse_abogado_export_file(Path(file_path))
        except McdiepVerificationError as exc:
            QMessageBox.critical(self, "No se pudo abrir el archivo", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if not rows:
            QMessageBox.warning(self, "Archivo vacío", "No se encontraron filas de datos en el archivo.")
            return

        abogado_id = self.abogado_combo.currentData()
        abogado = users_repo.get_by_id(abogado_id) if abogado_id else None

        revisiones_repo.add_revision_rows(
            agente_id=self.agente_user.id,
            source_filename=Path(file_path).name,
            abogado_nombre=abogado.full_name if abogado else None,
            rows=rows,
        )
        self._refresh_revision_table()
        QMessageBox.information(self, "Importado", f"Se importaron {len(rows)} filas para revisión.")

    def _refresh_revision_table(self) -> None:
        self.revision_table.setRowCount(0)
        rows = revisiones_repo.list_revision_rows(self.agente_user.id)
        for row in rows:
            r = self.revision_table.rowCount()
            self.revision_table.insertRow(r)
            values = [
                row.folio, row.cta_predial, row.contribuyente, row.domicilio,
                row.fecha_citatorio, row.recibe_citatorio, row.recibe_citatorio_nombre,
                row.fecha_notificacion, row.quien_recibe, row.quien_recibe_nombre,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.revision_table.setItem(r, col, item)

            procede_combo = QComboBox()
            for option in PROCEDE_OPTIONS:
                procede_combo.addItem(option, option or None)
            if row.procede:
                procede_combo.setCurrentIndex(procede_combo.findData(row.procede))
            procede_combo.currentIndexChanged.connect(
                lambda _i, row_id=row.id, combo=procede_combo: self._on_procede_changed(row_id, combo)
            )
            self.revision_table.setCellWidget(r, len(HEADERS_REVISION) - 1, procede_combo)

    def _on_procede_changed(self, row_id: int, combo: QComboBox) -> None:
        if self.simulate:
            return
        revisiones_repo.update_revision_procede(row_id, combo.currentData())

    def _on_export_revision(self) -> None:
        rows = revisiones_repo.list_revision_rows(self.agente_user.id)
        if not rows:
            QMessageBox.warning(self, "Nada que exportar", "Importe una captura del Abogado primero.")
            return

        if self.simulate:
            QMessageBox.information(
                self, "Simulación", f"Se habrían exportado {len(rows)} filas de revisión. No se exportó nada de verdad."
            )
            return

        fecha = datetime.now().strftime("%d_%m_%Y")
        output_path = exports_dir() / f"REVISION DEL {fecha}.xlsx"
        export_revision(rows, output_path)
        QMessageBox.information(self, "Exportado", f"Archivo exportado:\n{output_path}")
