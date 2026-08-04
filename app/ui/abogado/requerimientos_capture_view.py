"""Abogado: importa el archivo del Agente del PAE, captura el citatorio y exporta.

El Abogado nunca edita FOLIO/CTA PREDIAL/CONTRIBUYENTE/DOMICILIO (se muestran de
sólo lectura); captura dos pares de datos, cada uno con su propia fecha y
"quién recibe": la fecha/quién del citatorio en sí, y la fecha/quién de la
notificación de ese citatorio (dos eventos distintos).
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.recovery import open_email_client
from app.config import (
    BATCH_STATUS_EXPORTADO,
    QUIEN_RECIBE_EN_PUERTA,
    QUIEN_RECIBE_HOJA_CAMPO,
    QUIEN_RECIBE_NOMBRE,
)
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.requerimientos_export import build_abogado_envelope
from app.excel_io.requerimientos_import import McdiepVerificationError, parse_agente_export_file
from app.pdf_io import requerimientos_pdf
from app.utils.dates import format_local_datetime
from app.utils.paths import exports_dir

(
    COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM,
    COL_FECHA_CIT, COL_RECIBE_CIT, COL_NOMBRE_CIT,
    COL_FECHA_NOT, COL_QUIEN_NOT, COL_NOMBRE_NOT,
    COL_OBSERVACIONES,
) = range(11)
HEADERS = [
    "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO",
    "Fecha de citatorio", "Recibe citatorio", "Nombre",
    "Fecha de notificación", "Quién recibe", "Nombre",
    "Observaciones",
]

HIGHLIGHT_COLOR = QColor("#ffe08a")

DOC_TYPE_PENDIENTE = "PENDIENTE"
DOC_TYPE_EXPORTADO = "EXPORTADO"
DOC_TYPE_FINALIZADO = "FINALIZADO"
DOC_TYPES = (
    ("Pendiente", DOC_TYPE_PENDIENTE),
    ("Exportado", DOC_TYPE_EXPORTADO),
    ("Finalizado", DOC_TYPE_FINALIZADO),
)


def _category_for_batch(batch) -> str:
    if batch["finalizado"]:
        return DOC_TYPE_FINALIZADO
    if batch["status"] == BATCH_STATUS_EXPORTADO:
        return DOC_TYPE_EXPORTADO
    return DOC_TYPE_PENDIENTE


class RequerimientosCaptureView(QWidget):
    def __init__(self, abogado_user: users_repo.User, parent=None, simulate: bool = False):
        super().__init__(parent)
        self.abogado_user = abogado_user
        self.simulate = simulate
        self._current_batch_id: int | None = None
        self._current_batch_finalizado: bool = False
        self._rows: list[req_repo.RequerimientoRow] = []

        layout = QVBoxLayout(self)

        if self.simulate:
            banner = QLabel(
                "Modo simulación: puede navegar lotes existentes y probar la captura, pero "
                "nada de lo que haga aquí se guarda; no se pueden crear lotes nuevos."
            )
            banner.setStyleSheet(
                "background-color: rgba(255, 224, 138, 0.9); padding: 6px; border-radius: 4px;"
            )
            layout.addWidget(banner)

        import_row = QHBoxLayout()
        import_btn = QPushButton("Importar archivo del Agente del PAE")
        import_btn.clicked.connect(self._on_import)
        import_row.addWidget(import_btn)
        highlight_btn = QPushButton("Resaltar fila faltante de captura")
        highlight_btn.clicked.connect(self._on_highlight_missing)
        import_row.addWidget(highlight_btn)
        export_btn = QPushButton("Exportar")
        export_btn.setProperty("role", "primary")
        export_btn.clicked.connect(self._on_export)
        import_row.addWidget(export_btn)
        self.finalize_btn = QPushButton("Finalizar captura")
        self.finalize_btn.clicked.connect(self._on_finalize)
        import_row.addWidget(self.finalize_btn)
        self.edit_btn = QPushButton("Editar captura")
        self.edit_btn.clicked.connect(self._on_unlock_edit)
        self.edit_btn.setVisible(False)
        import_row.addWidget(self.edit_btn)
        layout.addLayout(import_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar por:"))
        self.search_field_combo = QComboBox()
        self.search_field_combo.addItem("FOLIO", COL_FOLIO)
        self.search_field_combo.addItem("CTA PREDIAL", COL_CTA)
        self.search_field_combo.addItem("CONTRIBUYENTE", COL_CONTRIB)
        search_row.addWidget(self.search_field_combo)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escriba para buscar y posicionarse en la fila...")
        self.search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self.search_input)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        # Pantalla previa: primero se elige QUÉ TIPO de documento se busca
        # (Pendiente/Exportado/Finalizado); sólo entonces se listan los lotes
        # de ese tipo. "Abrir" carga el seleccionado en la tabla de abajo;
        # "Limpiar" vacía la lista y cierra lo que estuviera abierto. Cambiar
        # el tipo directamente también vacía y vuelve a poblar la lista (ver
        # `_on_tipo_changed`), nunca mezcla tipos distintos en pantalla.
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Tipo de documento:"))
        self.tipo_combo = QComboBox()
        for label, value in DOC_TYPES:
            self.tipo_combo.addItem(label, value)
        self.tipo_combo.currentIndexChanged.connect(self._on_tipo_changed)
        selector_row.addWidget(self.tipo_combo)
        open_batch_btn = QPushButton("Abrir")
        open_batch_btn.clicked.connect(self._on_open_selected_batch)
        selector_row.addWidget(open_batch_btn)
        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self._on_clear)
        selector_row.addWidget(clear_btn)
        layout.addLayout(selector_row)

        self.available_list = QListWidget()
        self.available_list.setMaximumHeight(140)
        layout.addWidget(self.available_list)

        # Contadores del lote abierto: el "llenado" se mide únicamente por la
        # columna QUIÉN RECIBE (notificación) -- no exige el citatorio también,
        # a diferencia de is_captured usado por "Resaltar fila faltante".
        counters_row = QHBoxLayout()
        self.counters_label = QLabel()
        counters_row.addWidget(self.counters_label)
        counters_row.addStretch()
        layout.addLayout(counters_row)

        # Identidad del documento recibido del Agente (UUID + hash embebidos
        # en el .mcdiep importado) -- para comparar contra lo que muestra el
        # PDF físico que acompaña a ese mismo archivo.
        self.identity_label = QLabel()
        self.identity_label.setWordWrap(True)
        layout.addWidget(self.identity_label)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._refresh_available_list()
        self._update_counters()

    # --- Lotes -------------------------------------------------------------------
    def _refresh_available_list(self) -> None:
        self.available_list.clear()
        category = self.tipo_combo.currentData()
        for batch in req_repo.list_batches_for_abogado(self.abogado_user.id):
            if _category_for_batch(batch) != category:
                continue
            label = f"Lote #{batch['id']} — {batch['status']} — {format_local_datetime(batch['created_at'])}"
            item = QListWidgetItem(label)
            item.setData(1000, batch["id"])
            self.available_list.addItem(item)

    def _on_tipo_changed(self) -> None:
        # "Si se cambia directamente el tipo de documento, borre los archivos
        # disponibles": no se conserva la lista del tipo anterior.
        self._refresh_available_list()

    def _on_open_selected_batch(self) -> None:
        item = self.available_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "Nada seleccionado", "Seleccione un documento de la lista primero."
            )
            return
        self._load_batch(item.data(1000))

    def _on_clear(self) -> None:
        self.available_list.clear()
        self._current_batch_id = None
        self._rows = []
        self._current_batch_finalizado = False
        self.finalize_btn.setVisible(True)
        self.edit_btn.setVisible(False)
        self._update_identity_label(None)
        self._refresh_table()

    def _load_batch(self, batch_id: int) -> None:
        self._current_batch_id = batch_id
        self._rows = req_repo.list_rows(batch_id)
        batch = req_repo.get_batch(batch_id)
        self._current_batch_finalizado = bool(batch["finalizado"]) if batch else False
        self.finalize_btn.setVisible(not self._current_batch_finalizado)
        self.edit_btn.setVisible(self._current_batch_finalizado)
        self._update_identity_label(batch)
        self._refresh_table()

    def _update_identity_label(self, batch) -> None:
        if batch is None or not batch["agente_export_uuid"]:
            self.identity_label.setText("")
            return
        self.identity_label.setText(
            f"Documento recibido del Agente — UUID: {batch['agente_export_uuid']}  "
            f"Hash: {batch['agente_export_hash']}"
        )

    # --- Importar ------------------------------------------------------------------
    def _on_import(self) -> None:
        if self.simulate:
            QMessageBox.information(
                self, "No disponible en simulación",
                "En modo simulación no se pueden crear lotes nuevos. Puede navegar los lotes "
                "existentes de este usuario (lista de la izquierda) y simular su captura.",
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo del Agente del PAE", "", "Sistema PAE (*.mcdiep)"
        )
        if not file_path:
            return

        # No se pregunta "de qué Agente es" -- el propio archivo lo dice, de
        # forma verificable: sólo se abre si la firma es válida y el archivo
        # fue firmado específicamente para esta cuenta de Abogado.
        try:
            result = parse_agente_export_file(Path(file_path), abogado=self.abogado_user)
        except McdiepVerificationError as exc:
            QMessageBox.critical(self, "No se pudo abrir el archivo", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if not result.rows:
            QMessageBox.warning(self, "Archivo vacío", "No se encontraron filas de datos en el archivo.")
            return

        agente = result.agente
        batch_id = req_repo.create_batch(abogado_id=self.abogado_user.id, agente_id=agente.id)
        req_repo.add_rows(batch_id, result.rows)
        req_repo.record_imported_file(
            original_filename=Path(file_path).name, agente_id=agente.id, abogado_id=self.abogado_user.id,
            batch_id=batch_id, row_count=len(result.rows), original_path=file_path,
        )
        req_repo.set_batch_export_path(
            batch_id, agente_uuid=result.document_uuid, agente_hash=result.file_hash,
        )
        self.tipo_combo.setCurrentIndex(self.tipo_combo.findData(DOC_TYPE_PENDIENTE))
        self._refresh_available_list()
        self._load_batch(batch_id)
        for row in range(self.available_list.count()):
            if self.available_list.item(row).data(1000) == batch_id:
                self.available_list.setCurrentRow(row)
                break
        QMessageBox.information(
            self, "Importado",
            f"Se importaron {len(result.rows)} filas al lote #{batch_id}.\n\n"
            f"Firmado por: {agente.full_name} ({agente.username}).\n\n"
            f"UUID: {result.document_uuid}\nHash: {result.file_hash}",
        )

    # --- Tabla de captura ------------------------------------------------------------
    def _update_counters(self) -> None:
        total = len(self._rows)
        llenados = sum(1 for row in self._rows if row.quien_recibe)
        faltan = total - llenados
        self.counters_label.setText(
            f"Total de la lista: {total}    |    Total de llenados: {llenados}    |    "
            f"Faltan por llenarse: {faltan}"
        )

    def _refresh_table(self) -> None:
        self._update_counters()
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self._rows))
            for r, row in enumerate(self._rows):
                self.table.setItem(r, COL_FOLIO, QTableWidgetItem(row.folio or ""))
                self.table.setItem(r, COL_CTA, QTableWidgetItem(row.cta_predial or ""))
                self.table.setItem(r, COL_CONTRIB, QTableWidgetItem(row.contribuyente or ""))
                self.table.setItem(r, COL_DOM, QTableWidgetItem(row.domicilio or ""))

                self._build_capture_trio(
                    r, row.id,
                    date_col=COL_FECHA_CIT, combo_col=COL_RECIBE_CIT, name_col=COL_NOMBRE_CIT,
                    fecha_value=row.fecha_citatorio, quien_value=row.recibe_citatorio,
                    nombre_value=row.recibe_citatorio_nombre,
                )
                self._build_capture_trio(
                    r, row.id,
                    date_col=COL_FECHA_NOT, combo_col=COL_QUIEN_NOT, name_col=COL_NOMBRE_NOT,
                    fecha_value=row.fecha_notificacion, quien_value=row.quien_recibe,
                    nombre_value=row.quien_recibe_nombre,
                )
                self._build_observaciones_cell(r, row.id, row.observaciones)
        finally:
            self.table.setUpdatesEnabled(True)

    def _build_capture_trio(
        self, table_row: int, row_id: int, *, date_col: int, combo_col: int, name_col: int,
        fecha_value: str | None, quien_value: str | None, nombre_value: str | None,
    ) -> None:
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd/MM/yyyy")
        if fecha_value:
            date_edit.setDate(QDate.fromString(fecha_value, "dd/MM/yyyy"))
        else:
            date_edit.setDate(QDate.currentDate())
        date_edit.setEnabled(not self._current_batch_finalizado)
        date_edit.dateChanged.connect(lambda _d, rid=row_id: self._save_row(rid))
        self.table.setCellWidget(table_row, date_col, date_edit)

        quien_combo = QComboBox()
        quien_combo.addItem("", "")
        quien_combo.addItem(QUIEN_RECIBE_EN_PUERTA, QUIEN_RECIBE_EN_PUERTA)
        quien_combo.addItem(QUIEN_RECIBE_NOMBRE, QUIEN_RECIBE_NOMBRE)
        quien_combo.addItem(QUIEN_RECIBE_HOJA_CAMPO, QUIEN_RECIBE_HOJA_CAMPO)
        if quien_value:
            quien_combo.setCurrentIndex(quien_combo.findData(quien_value))
        quien_combo.setEnabled(not self._current_batch_finalizado)
        self.table.setCellWidget(table_row, combo_col, quien_combo)

        nombre_edit = QLineEdit(nombre_value or "")
        nombre_edit.setEnabled(quien_value == QUIEN_RECIBE_NOMBRE and not self._current_batch_finalizado)
        self.table.setCellWidget(table_row, name_col, nombre_edit)

        quien_combo.currentIndexChanged.connect(
            lambda _i, rid=row_id, combo=quien_combo, name_edit=nombre_edit: self._on_quien_changed(
                rid, combo, name_edit
            )
        )
        nombre_edit.textChanged.connect(lambda text, rid=row_id, edit=nombre_edit: self._on_nombre_changed(rid, text, edit))

    def _build_observaciones_cell(self, table_row: int, row_id: int, value: str | None) -> None:
        observaciones_edit = QLineEdit(value or "")
        observaciones_edit.setEnabled(not self._current_batch_finalizado)
        observaciones_edit.editingFinished.connect(lambda rid=row_id: self._save_row(rid))
        self.table.setCellWidget(table_row, COL_OBSERVACIONES, observaciones_edit)

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
        if self._current_batch_finalizado and not self.simulate:
            return
        table_row = self._table_row_for_id(row_id)
        if table_row is None:
            return

        fecha_citatorio, recibe_citatorio, recibe_citatorio_nombre = self._read_capture_trio(
            table_row, date_col=COL_FECHA_CIT, combo_col=COL_RECIBE_CIT, name_col=COL_NOMBRE_CIT
        )
        fecha_notificacion, quien_recibe, quien_recibe_nombre = self._read_capture_trio(
            table_row, date_col=COL_FECHA_NOT, combo_col=COL_QUIEN_NOT, name_col=COL_NOMBRE_NOT
        )
        observaciones_edit: QLineEdit = self.table.cellWidget(table_row, COL_OBSERVACIONES)
        observaciones = observaciones_edit.text().strip() or None

        if not self.simulate:
            req_repo.update_row_capture(
                row_id,
                fecha_citatorio=fecha_citatorio,
                recibe_citatorio=recibe_citatorio,
                recibe_citatorio_nombre=recibe_citatorio_nombre,
                fecha_notificacion=fecha_notificacion,
                quien_recibe=quien_recibe,
                quien_recibe_nombre=quien_recibe_nombre,
                observaciones=observaciones,
            )
        for row in self._rows:
            if row.id == row_id:
                row.fecha_citatorio = fecha_citatorio
                row.recibe_citatorio = recibe_citatorio
                row.recibe_citatorio_nombre = recibe_citatorio_nombre
                row.fecha_notificacion = fecha_notificacion
                row.quien_recibe = quien_recibe
                row.quien_recibe_nombre = quien_recibe_nombre
                row.observaciones = observaciones
                break
        self._update_counters()

    def _read_capture_trio(
        self, table_row: int, *, date_col: int, combo_col: int, name_col: int
    ) -> tuple[str | None, str | None, str | None]:
        date_edit: QDateEdit = self.table.cellWidget(table_row, date_col)
        quien_combo: QComboBox = self.table.cellWidget(table_row, combo_col)
        nombre_edit: QLineEdit = self.table.cellWidget(table_row, name_col)

        quien_value = quien_combo.currentData() or None
        fecha_value = date_edit.date().toString("dd/MM/yyyy") if quien_value else None
        nombre_value = nombre_edit.text().strip() or None if quien_value == QUIEN_RECIBE_NOMBRE else None
        return fecha_value, quien_value, nombre_value

    def _table_row_for_id(self, row_id: int) -> int | None:
        for idx, row in enumerate(self._rows):
            if row.id == row_id:
                return idx
        return None

    # --- Resaltar faltantes / buscar ---------------------------------------------------
    def _flash_highlight(self, row_index: int, columns: tuple[int, ...]) -> None:
        original_colors = []
        for col in columns:
            item = self.table.item(row_index, col)
            original_colors.append(item.background())
            item.setBackground(HIGHLIGHT_COLOR)

        def revert():
            for col, color in zip(columns, original_colors):
                item = self.table.item(row_index, col)
                if item is not None:
                    item.setBackground(color)

        QTimer.singleShot(1000, revert)

    def _on_highlight_missing(self) -> None:
        missing_index = next((i for i, row in enumerate(self._rows) if not row.is_captured), None)
        if missing_index is None:
            QMessageBox.information(self, "Captura completa", "No hay filas pendientes de captura en este lote.")
            return

        self.table.scrollToItem(self.table.item(missing_index, COL_FOLIO))
        self.table.selectRow(missing_index)
        self._flash_highlight(missing_index, (COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM))

    def _on_search(self) -> None:
        text = self.search_input.text().strip().lower()
        if not text:
            return

        col = self.search_field_combo.currentData()
        field_by_col = {COL_FOLIO: "folio", COL_CTA: "cta_predial", COL_CONTRIB: "contribuyente"}
        for row_index, row in enumerate(self._rows):
            value = getattr(row, field_by_col[col]) or ""
            if text in value.lower():
                self.table.scrollToItem(self.table.item(row_index, col))
                self.table.selectRow(row_index)
                self._flash_highlight(row_index, (COL_FOLIO, COL_CTA, COL_CONTRIB, COL_DOM))
                return

        QMessageBox.information(self, "Sin resultados", "No se encontró ninguna fila que coincida con la búsqueda.")

    # --- Finalizar / editar --------------------------------------------------------------
    def _on_finalize(self) -> None:
        if self._current_batch_id is None:
            QMessageBox.warning(self, "Nada que finalizar", "Seleccione un lote primero.")
            return
        if self.simulate:
            QMessageBox.information(
                self, "No disponible en simulación",
                "En modo simulación no se puede finalizar ni desbloquear un lote.",
            )
            return

        reply = QMessageBox.question(
            self, "Finalizar captura",
            "¿Finalizar la captura de este lote? No se podrán modificar las filas hasta "
            "que use 'Editar captura' para desbloquearlo.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        req_repo.set_batch_finalizado(self._current_batch_id, True)
        self._current_batch_finalizado = True
        self.finalize_btn.setVisible(False)
        self.edit_btn.setVisible(True)
        self._refresh_table()
        self._refresh_available_list()

    def _on_unlock_edit(self) -> None:
        if self._current_batch_id is None:
            return
        if self.simulate:
            QMessageBox.information(
                self, "No disponible en simulación",
                "En modo simulación no se puede finalizar ni desbloquear un lote.",
            )
            return

        # Si el lote YA se exportó antes, desbloquearlo para editar no
        # actualiza solo el archivo que ya se entregó -- hay que avisarlo
        # explícitamente antes de permitirlo (a diferencia de un lote que
        # sólo se finalizó manualmente sin haberse exportado todavía).
        batch = req_repo.get_batch(self._current_batch_id)
        if batch is not None and batch["status"] == BATCH_STATUS_EXPORTADO:
            proceed = QMessageBox.warning(
                self, "Lote ya exportado",
                "Este lote ya se exportó anteriormente. Si edita la captura ahora, el "
                "archivo que ya se exportó NO se actualiza solo: deberá volver a "
                "exportarlo cuando termine sus cambios.\n\n"
                "¿Desea desbloquear la captura de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        req_repo.set_batch_finalizado(self._current_batch_id, False)
        self._current_batch_finalizado = False
        self.finalize_btn.setVisible(True)
        self.edit_btn.setVisible(False)
        self._refresh_table()
        self._refresh_available_list()

    # --- Exportar ------------------------------------------------------------------------
    def _ask_export_choice(self) -> str:
        """Devuelve 'email', 'only' o 'cancel'. Aislado en su propio método para
        que las pruebas puedan simular la elección sin abrir un diálogo real."""
        choice_box = QMessageBox(self)
        choice_box.setWindowTitle("Exportar")
        choice_box.setText("¿Cómo deseas exportar la captura de este lote?")
        email_btn = choice_box.addButton("Exportar y enviar por correo", QMessageBox.ButtonRole.AcceptRole)
        only_btn = choice_box.addButton("Sólo exportar", QMessageBox.ButtonRole.ActionRole)
        choice_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        choice_box.exec()
        clicked = choice_box.clickedButton()
        if clicked is email_btn:
            return "email"
        if clicked is only_btn:
            return "only"
        return "cancel"

    def _on_export(self) -> None:
        if self._current_batch_id is None or not self._rows:
            QMessageBox.warning(self, "Nada que exportar", "Seleccione un lote con filas capturadas.")
            return

        if self.simulate:
            QMessageBox.information(
                self, "Simulación",
                f"Se habría exportado el lote #{self._current_batch_id}. No se guardó ni "
                "exportó nada de verdad.",
            )
            return

        rows_to_export = [row for row in self._rows if row.is_modified]
        if not rows_to_export:
            QMessageBox.warning(
                self, "Nada que exportar",
                "Ninguna fila de este lote tiene captura registrada todavía.",
            )
            return

        choice = self._ask_export_choice()
        if choice == "cancel":
            return

        batch = req_repo.get_batch(self._current_batch_id)
        agente = users_repo.get_by_id(batch["agente_id"])

        document_uuid = requerimientos_pdf.new_document_uuid()
        envelope = build_abogado_envelope(rows_to_export, document_uuid=document_uuid)
        mcdiep_bytes = mcdiep_format.envelope_bytes(envelope)
        identity = requerimientos_pdf.compute_identity(mcdiep_bytes, document_uuid=document_uuid)
        filename = requerimientos_pdf.suggested_filename(
            agente_nombre=agente.full_name, abogado_nombre=self.abogado_user.full_name,
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

        output_path.write_bytes(mcdiep_bytes)
        req_repo.set_batch_export_path(
            self._current_batch_id, abogado_path=str(output_path),
            abogado_uuid=identity.uuid, abogado_hash=identity.file_hash,
        )
        req_repo.set_batch_status(self._current_batch_id, BATCH_STATUS_EXPORTADO)
        pdf_path = output_path.with_suffix(".pdf")
        requerimientos_pdf.export_abogado_pdf(
            pdf_path, agente=agente, abogado=self.abogado_user, rows=rows_to_export,
            filename=output_path.name, identity=identity,
        )

        # Los datos ya exportados quedan bloqueados de inmediato -- igual que
        # "Finalizar captura" -- para que no se editen por accidente después
        # de entregados; "Editar captura" los desbloquea (con advertencia).
        req_repo.set_batch_finalizado(self._current_batch_id, True)
        self._current_batch_finalizado = True
        self.finalize_btn.setVisible(False)
        self.edit_btn.setVisible(True)
        self._refresh_table()
        self._refresh_available_list()

        identity_note = f"\nPDF: {pdf_path}\n\nUUID: {identity.uuid}\nHash: {identity.file_hash}"
        locked_note = "\n\nEl lote quedó bloqueado; use 'Editar captura' para modificarlo."
        if choice == "email":
            if agente.email:
                open_email_client(
                    to_email=agente.email,
                    subject="Entrega de Requerimientos capturados",
                    body=f"Se adjunta la captura del lote #{self._current_batch_id}.",
                    attachment_path=output_path,
                )
                QMessageBox.information(
                    self, "Exportado",
                    f"Archivo exportado y correo abierto:\n{output_path}{identity_note}{locked_note}",
                )
            else:
                QMessageBox.warning(
                    self, "Sin correo del Agente",
                    "El archivo se exportó, pero el Agente del PAE de este lote no tiene correo "
                    f"registrado, así que no se pudo abrir el correo:\n{output_path}{identity_note}{locked_note}",
                )
        else:
            QMessageBox.information(
                self, "Exportado", f"Archivo exportado:\n{output_path}{identity_note}{locked_note}"
            )
