"""Agente del PAE: seguimiento de documentos en 4 estados -- GENERADOS (lotes
exportados en "Generar Formato"), EN REVISIÓN, PENDIENTES DE ENVIAR COMO
REPORTE y REPORTES ENVIADOS (estos 3 últimos, del ciclo de "Revisar Formato").
Es un panel de consulta y navegación rápida aparte de esas dos pantallas, no
las reemplaza."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.repositories import requerimientos as req_repo
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.requerimientos_export import build_agente_envelope
from app.pdf_io import requerimientos_pdf
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog
from app.utils.dates import format_local_datetime
from app.utils.paths import exports_dir

STATE_GENERADOS = "GENERADOS"
STATE_EN_REVISION = revisiones_repo.STATUS_EN_REVISION
STATE_PENDIENTE_REPORTE = revisiones_repo.STATUS_PENDIENTE_REPORTE
STATE_REPORTE_ENVIADO = revisiones_repo.STATUS_REPORTE_ENVIADO

SEGUIMIENTO_STATES = (
    ("Generados", STATE_GENERADOS),
    ("En revisión", STATE_EN_REVISION),
    ("Pendientes de enviar como reporte", STATE_PENDIENTE_REPORTE),
    ("Reportes enviados", STATE_REPORTE_ENVIADO),
)

ACTION_LABEL_BY_STATE = {
    STATE_GENERADOS: "Volver a exportar",
    STATE_EN_REVISION: "Continuar captura",
    STATE_PENDIENTE_REPORTE: "Exportar como reporte",
    STATE_REPORTE_ENVIADO: "Volver a generar archivo",
}

COL_ARCHIVO, COL_ABOGADO, COL_CARGADO, COL_ESTATUS = range(4)
HEADERS = ["Archivo", "Abogado", "Cargado", "Estatus cambiado"]


class SeguimientoView(QWidget):
    # Emitida al pedir "Continuar captura" sobre un archivo EN REVISIÓN -- la
    # ventana que aloja esta vista debe cambiar a "Revisar Formato
    # Requerimiento" y abrir ahí ese archivo (ver
    # MainWindow._on_continuar_revision_solicitada).
    continuar_revision_solicitada = Signal(int)

    def __init__(self, agente_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.agente_user = agente_user
        self._current_ids: list[int] = []  # ids por fila de la tabla, mismo orden

        layout = QVBoxLayout(self)

        self.tipo_tabs = QTabWidget()
        layout.addWidget(self.tipo_tabs)

        requerimiento_page = QWidget()
        requerimiento_layout = QVBoxLayout(requerimiento_page)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Estado:"))
        self.estado_combo = QComboBox()
        for label, value in SEGUIMIENTO_STATES:
            self.estado_combo.addItem(label, value)
        self.estado_combo.currentIndexChanged.connect(self._on_estado_changed)
        selector_row.addWidget(self.estado_combo)
        self.action_btn = QPushButton()
        self.action_btn.clicked.connect(self._on_action_clicked)
        selector_row.addWidget(self.action_btn)
        requerimiento_layout.addLayout(selector_row)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        requerimiento_layout.addWidget(self.table)

        self.tipo_tabs.addTab(requerimiento_page, "Requerimiento")

        mandamiento_page = QLabel(
            "El seguimiento del Formato de Mandamientos se agregará en una siguiente "
            "fase del programa."
        )
        mandamiento_page.setWordWrap(True)
        mandamiento_page.setContentsMargins(16, 16, 16, 16)
        self.tipo_tabs.addTab(mandamiento_page, "Mandamiento (Próximamente)")

        self._refresh_table()

    # --- Listado por estado -----------------------------------------------------------
    def _on_estado_changed(self) -> None:
        self._refresh_table()

    def _refresh_table(self) -> None:
        estado = self.estado_combo.currentData()
        self.action_btn.setText(ACTION_LABEL_BY_STATE[estado])

        if estado == STATE_GENERADOS:
            entries = [
                (
                    batch["id"],
                    Path(batch["exported_agente_path"]).name
                    if batch["exported_agente_path"] else f"Lote #{batch['id']}",
                    batch["abogado_nombre"] or "",
                    batch["created_at"],
                    batch["updated_at"],
                )
                for batch in req_repo.list_batches_for_agente(self.agente_user.id)
            ]
        else:
            entries = [
                (
                    imp.id, imp.source_filename, imp.abogado_nombre or "",
                    imp.imported_at, imp.status_changed_at,
                )
                for imp in revisiones_repo.list_revision_imports(self.agente_user.id)
                if imp.status == estado
            ]

        self._current_ids = [entry[0] for entry in entries]
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(entries))
            for r, (_id, archivo, abogado, cargado, estatus_cambiado) in enumerate(entries):
                self.table.setItem(r, COL_ARCHIVO, QTableWidgetItem(archivo))
                self.table.setItem(r, COL_ABOGADO, QTableWidgetItem(abogado))
                self.table.setItem(r, COL_CARGADO, QTableWidgetItem(format_local_datetime(cargado)))
                self.table.setItem(r, COL_ESTATUS, QTableWidgetItem(format_local_datetime(estatus_cambiado)))
        finally:
            self.table.setUpdatesEnabled(True)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_ids):
            return None
        return self._current_ids[row]

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._on_action_clicked()

    # --- Acciones por estado -----------------------------------------------------------
    def _on_action_clicked(self) -> None:
        target_id = self._selected_id()
        if target_id is None:
            QMessageBox.information(self, "Nada seleccionado", "Seleccione un archivo de la lista primero.")
            return

        estado = self.estado_combo.currentData()
        if estado == STATE_GENERADOS:
            self._reexport_batch(target_id)
        elif estado == STATE_EN_REVISION:
            self.continuar_revision_solicitada.emit(target_id)
        elif estado == STATE_PENDIENTE_REPORTE:
            QMessageBox.information(
                self, "Próximamente",
                "La exportación como reporte todavía no está disponible -- se necesita más "
                "planeación para esta fase del programa.",
            )
        else:  # STATE_REPORTE_ENVIADO
            QMessageBox.information(
                self, "Sin reportes enviados",
                "Todavía no hay reportes enviados -- esta etapa se habilita junto con la "
                "exportación como reporte.",
            )

    def _reexport_batch(self, batch_id: int) -> None:
        batch = req_repo.get_batch(batch_id)
        if batch is None:
            QMessageBox.warning(self, "No encontrado", "Este lote ya no existe.")
            self._refresh_table()
            return

        abogado = users_repo.get_by_id(batch["abogado_id"])
        rows = req_repo.list_rows(batch_id)
        if not rows:
            QMessageBox.warning(self, "Sin filas", "Este lote no tiene filas que exportar.")
            return

        proceed = QMessageBox.question(
            self, "Volver a exportar",
            f"¿Volver a exportar este documento para {abogado.full_name}? Se generará un "
            "archivo nuevo, firmado de nuevo con su certificado actual.",
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
                "El archivo que se va a volver a exportar queda firmado con su certificado. "
                "Confirme su identidad con su certificado actual."
            ),
        )
        if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        row_dicts = [
            {
                "folio": row.folio, "cta_predial": row.cta_predial,
                "contribuyente": row.contribuyente, "domicilio": row.domicilio,
            }
            for row in rows
        ]
        document_uuid = requerimientos_pdf.new_document_uuid()
        envelope = build_agente_envelope(
            row_dicts, agente=self.agente_user, abogado=abogado,
            private_key=confirm_dialog.private_key, document_uuid=document_uuid,
        )
        mcdiep_bytes = mcdiep_format.envelope_bytes(envelope)
        identity = requerimientos_pdf.compute_identity(
            mcdiep_bytes, document_uuid=document_uuid, private_key=confirm_dialog.private_key,
        )
        suggested_name = requerimientos_pdf.suggested_filename(
            agente_nombre=self.agente_user.full_name, abogado_nombre=abogado.full_name,
            identity=identity, extension=mcdiep_format.EXTENSION,
        )
        suggested_path = exports_dir() / suggested_name
        output_path_str, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", str(suggested_path), f"Sistema PAE (*{mcdiep_format.EXTENSION})",
        )
        if not output_path_str:
            return
        output_path = Path(output_path_str)

        output_path.write_bytes(mcdiep_bytes)
        req_repo.set_batch_export_path(
            batch_id, agente_path=str(output_path),
            agente_uuid=identity.uuid, agente_hash=identity.file_hash,
        )
        pdf_path = output_path.with_suffix(".pdf")
        requerimientos_pdf.export_agente_pdf(
            pdf_path, agente=self.agente_user, abogado=abogado, rows=row_dicts,
            filename=output_path.name, identity=identity,
        )

        QMessageBox.information(
            self, "Exportado",
            f"Se volvió a exportar el documento:\n{output_path}\nPDF: {pdf_path}\n\n"
            f"UUID: {identity.uuid}\nHash: {identity.file_hash}",
        )
        self._refresh_table()
