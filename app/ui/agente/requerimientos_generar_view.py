"""Agente del PAE: selecciona abogado, carga Excel y exporta el formato firmado."""

from __future__ import annotations

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
from app.excel_io.requerimientos_export import build_agente_envelope
from app.excel_io.requerimientos_import import parse_requerimientos_file
from app.pdf_io import requerimientos_pdf
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog
from app.utils.paths import exports_dir


class RequerimientosGenerarView(QWidget):
    def __init__(self, agente_user: users_repo.User, parent=None, simulate: bool = False, dummy: bool = False):
        super().__init__(parent)
        self.agente_user = agente_user
        self.simulate = simulate
        self.dummy = dummy
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
        elif self.dummy:
            banner = QLabel(
                "Cuenta de prueba: al exportar se genera un archivo real (una sola página, "
                "sin certificado ni firma, con UUID/hash de prueba y marca de agua), pero "
                "nada queda registrado en la base de datos del programa."
            )
            banner.setWordWrap(True)
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
        export_btn.setProperty("role", "primary")
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

            if not self.simulate and not self.dummy:
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
        elif self.dummy:
            proceed = QMessageBox.question(
                self, "Confirmar exportación de prueba",
                f"Se generará un archivo de prueba real (máximo {requerimientos_pdf.DUMMY_MAX_ROWS} "
                "filas, una sola página, sin certificado ni firma, con UUID/hash de prueba y "
                "marca de agua) para verificar el formato. No queda registrado nada en la base "
                "de datos.\n\n¿Continuar?",
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

            dummy_rows = self._rows[: requerimientos_pdf.DUMMY_MAX_ROWS]
            identity = requerimientos_pdf.dummy_identity()
            envelope = build_agente_envelope(
                dummy_rows, agente=self.agente_user, abogado=abogado,
                private_key=None, document_uuid=identity.uuid,
            )
            mcdiep_bytes = mcdiep_format.envelope_bytes(envelope)
            filename = requerimientos_pdf.suggested_dummy_filename(
                agente_nombre=self.agente_user.full_name, abogado_nombre=abogado.full_name,
                extension=mcdiep_format.EXTENSION,
            )
            folder = QFileDialog.getExistingDirectory(
                self, "Elegir carpeta para guardar el archivo de prueba", str(exports_dir())
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

            output_path.write_bytes(mcdiep_bytes)
            pdf_path = output_path.with_suffix(".pdf")
            requerimientos_pdf.export_agente_pdf(
                pdf_path, agente=self.agente_user, abogado=abogado, rows=dummy_rows,
                filename=output_path.name, identity=identity,
                dummy=True, watermark_text=f"PAE PRUEBA - {self.agente_user.full_name}",
            )

            QMessageBox.information(
                self, "Exportado (prueba)",
                f"Archivo de prueba generado ({len(dummy_rows)} filas):\n{output_path}\n"
                f"PDF: {pdf_path}\n\nUUID: {identity.uuid}\nHash: {identity.file_hash}\n\n"
                "No se guardó ningún dato en la base de datos.",
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

            document_uuid = requerimientos_pdf.new_document_uuid()
            envelope = build_agente_envelope(
                self._rows, agente=self.agente_user, abogado=abogado,
                private_key=confirm_dialog.private_key, document_uuid=document_uuid,
            )
            mcdiep_bytes = mcdiep_format.envelope_bytes(envelope)
            identity = requerimientos_pdf.compute_identity(
                mcdiep_bytes, document_uuid=document_uuid, private_key=confirm_dialog.private_key,
            )
            filename = requerimientos_pdf.suggested_filename(
                agente_nombre=self.agente_user.full_name, abogado_nombre=abogado.full_name,
                identity=identity, extension=mcdiep_format.EXTENSION,
            )
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

            output_path.write_bytes(mcdiep_bytes)
            req_repo.set_batch_export_path(
                batch_id, agente_path=str(output_path),
                agente_uuid=identity.uuid, agente_hash=identity.file_hash,
            )
            pdf_path = output_path.with_suffix(".pdf")
            requerimientos_pdf.export_agente_pdf(
                pdf_path, agente=self.agente_user, abogado=abogado, rows=self._rows,
                filename=output_path.name, identity=identity,
            )

            QMessageBox.information(
                self, "Exportado",
                f"Se exportaron y firmaron {len(self._rows)} filas para {abogado.full_name}:\n{output_path}\n"
                f"PDF: {pdf_path}\n\nUUID: {identity.uuid}\nHash: {identity.file_hash}",
            )

        self._rows = []
        self._source_filenames = []
        self._refresh_preview()
