"""Agente del PAE: seguimiento de documentos en 4 estados -- GENERADOS (lotes
exportados en "Generar Formato"), EN REVISIÓN, PENDIENTES DE ENVIAR COMO
REPORTE y REPORTES ENVIADOS (estos 3 últimos, del ciclo de "Revisar Formato").
Es un panel de consulta y navegación rápida aparte de esas dos pantallas, no
las reemplaza. Una pestaña por tipo de documento (Requerimiento/Mandamiento),
cada una respaldada por su propio par de repositorios."""

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

from app.db.repositories import mandamientos as mand_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import revisiones_mandamiento as revisiones_mandamiento_repo
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.mandamientos_export import build_agente_envelope as build_agente_mandamiento_envelope
from app.excel_io.requerimientos_export import build_agente_envelope as build_agente_requerimiento_envelope
from app.pdf_io import mandamientos_pdf, requerimientos_pdf
from app.ui.widgets.certificate_confirm_dialog import CertificateConfirmDialog
from app.utils.dates import format_local_datetime
from app.utils.paths import exports_dir

STATE_GENERADOS = "GENERADOS"
STATE_EN_REVISION = "EN_REVISION"
STATE_PENDIENTE_REPORTE = "PENDIENTE_REPORTE"
STATE_REPORTE_ENVIADO = "REPORTE_ENVIADO"

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


class _SeguimientoTipoPage(QWidget):
    """Una pestaña de seguimiento para UN tipo de documento (Requerimiento o
    Mandamiento) -- misma lógica, sólo cambian los repositorios/módulo de PDF
    que recibe por parámetro."""

    continuar_revision_solicitada = Signal(int)

    def __init__(
        self, agente_user: users_repo.User, *, batch_repo, revision_repo,
        build_agente_envelope, pdf_module, row_to_dict, parent=None,
    ):
        super().__init__(parent)
        self.agente_user = agente_user
        self.batch_repo = batch_repo
        self.revision_repo = revision_repo
        self.build_agente_envelope = build_agente_envelope
        self.pdf_module = pdf_module
        self.row_to_dict = row_to_dict
        self._current_ids: list[int] = []  # ids por fila de la tabla, mismo orden

        layout = QVBoxLayout(self)

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
        layout.addLayout(selector_row)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        self.refresh_table()

    # --- Listado por estado -----------------------------------------------------------
    def _on_estado_changed(self) -> None:
        self.refresh_table()

    def refresh_table(self) -> None:
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
                for batch in self.batch_repo.list_batches_for_agente(self.agente_user.id)
            ]
        else:
            entries = [
                (
                    imp.id, imp.source_filename, imp.abogado_nombre or "",
                    imp.imported_at, imp.status_changed_at,
                )
                for imp in self.revision_repo.list_revision_imports(self.agente_user.id)
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
        batch = self.batch_repo.get_batch(batch_id)
        if batch is None:
            QMessageBox.warning(self, "No encontrado", "Este lote ya no existe.")
            self.refresh_table()
            return

        abogado = users_repo.get_by_id(batch["abogado_id"])
        rows = self.batch_repo.list_rows(batch_id)
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

        row_dicts = [self.row_to_dict(row) for row in rows]
        document_uuid = self.pdf_module.new_document_uuid()
        envelope = self.build_agente_envelope(
            row_dicts, agente=self.agente_user, abogado=abogado,
            private_key=confirm_dialog.private_key, document_uuid=document_uuid,
        )
        mcdiep_bytes = mcdiep_format.envelope_bytes(envelope)
        identity = self.pdf_module.compute_identity(
            mcdiep_bytes, document_uuid=document_uuid, private_key=confirm_dialog.private_key,
        )
        suggested_name = self.pdf_module.suggested_filename(
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
        self.batch_repo.set_batch_export_path(
            batch_id, agente_path=str(output_path),
            agente_uuid=identity.uuid, agente_hash=identity.file_hash,
        )
        pdf_path = output_path.with_suffix(".pdf")
        self.pdf_module.export_agente_pdf(
            pdf_path, agente=self.agente_user, abogado=abogado, rows=row_dicts,
            filename=output_path.name, identity=identity,
        )

        QMessageBox.information(
            self, "Exportado",
            f"Se volvió a exportar el documento:\n{output_path}\nPDF: {pdf_path}\n\n"
            f"UUID: {identity.uuid}\nHash: {identity.file_hash}",
        )
        self.refresh_table()


class SeguimientoView(QWidget):
    # Emitida al pedir "Continuar captura" sobre un archivo EN REVISIÓN --
    # lleva el tipo ("requerimiento"/"mandamiento") y el id del import, para
    # que la ventana que aloja esta vista abra la pantalla de "Revisar
    # Formato" correcta con ese archivo (ver
    # MainWindow._on_continuar_revision_solicitada).
    continuar_revision_solicitada = Signal(str, int)

    def __init__(self, agente_user: users_repo.User, parent=None):
        super().__init__(parent)
        self.agente_user = agente_user

        layout = QVBoxLayout(self)

        self.tipo_tabs = QTabWidget()
        layout.addWidget(self.tipo_tabs)

        self.requerimiento_page = _SeguimientoTipoPage(
            agente_user, batch_repo=req_repo, revision_repo=revisiones_repo,
            build_agente_envelope=build_agente_requerimiento_envelope, pdf_module=requerimientos_pdf,
            row_to_dict=lambda row: {
                "folio": row.folio, "cta_predial": row.cta_predial,
                "contribuyente": row.contribuyente, "domicilio": row.domicilio,
            },
        )
        self.requerimiento_page.continuar_revision_solicitada.connect(
            lambda rid: self.continuar_revision_solicitada.emit("requerimiento", rid)
        )
        self.tipo_tabs.addTab(self.requerimiento_page, "Requerimiento")

        self.mandamiento_page = _SeguimientoTipoPage(
            agente_user, batch_repo=mand_repo, revision_repo=revisiones_mandamiento_repo,
            build_agente_envelope=build_agente_mandamiento_envelope, pdf_module=mandamientos_pdf,
            row_to_dict=lambda row: {
                "folio": row.folio, "cta_predial": row.cta_predial, "contribuyente": row.contribuyente,
            },
        )
        self.mandamiento_page.continuar_revision_solicitada.connect(
            lambda rid: self.continuar_revision_solicitada.emit("mandamiento", rid)
        )
        self.tipo_tabs.addTab(self.mandamiento_page, "Mandamiento")
