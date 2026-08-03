"""Agente del PAE: revisa la captura que exportó el Abogado y marca PROCEDE/NO
PROCEDE, para Mandamiento. Mismo flujo que
app/ui/agente/requerimientos_revision_view.py."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
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

from app.config import ROLE_ABOGADO
from app.db.repositories import revisiones_mandamiento as revisiones_repo
from app.db.repositories import users as users_repo
from app.excel_io.mandamientos_export import HEADERS_REVISION, export_revision
from app.excel_io.mandamientos_import import McdiepVerificationError, parse_abogado_export_file
from app.utils.dates import format_local_datetime
from app.utils.paths import exports_dir

PROCEDE_OPTIONS = ("", "PROCEDE", "NO PROCEDE")
HIGHLIGHT_COLOR = QColor("#ffe08a")
# Índices de columna de HEADERS_REVISION (= HEADERS_ABOGADO + ["Procede", "ID Abogado"]).
REVISION_SEARCH_COLUMNS = {"FOLIO": 0, "CTA PREDIAL": 1, "CONTRIBUYENTE": 2}

SIN_ARCHIVO_TEXT = "Archivo en revisión: (ninguno)"

DOC_STATE_PENDIENTE = "PENDIENTE"
DOC_STATE_REVISADO = "REVISADO"
DOC_STATES = (
    ("Pendiente", DOC_STATE_PENDIENTE),
    ("Revisado", DOC_STATE_REVISADO),
)


class MandamientosRevisionView(QWidget):
    # Emite el nombre del archivo actualmente abierto (o "" tras limpiar/sin
    # selección), para que la ventana que aloja esta vista (una pestaña)
    # pueda reflejarlo en su título -- ver MainWindow._show_revisar_mandamiento_tab.
    archivo_cambiado = Signal(str)

    def __init__(self, agente_user: users_repo.User, parent=None, simulate: bool = False):
        super().__init__(parent)
        self.agente_user = agente_user
        self.simulate = simulate
        self._current_import_id: int | None = None

        layout = QVBoxLayout(self)

        if self.simulate:
            banner = QLabel(
                "Modo simulación: puede navegar archivos ya importados y probar el flujo, "
                "pero nada de lo que haga aquí se guarda; no se pueden importar archivos nuevos."
            )
            banner.setStyleSheet(
                "background-color: rgba(255, 224, 138, 0.9); padding: 6px; border-radius: 4px;"
            )
            layout.addWidget(banner)

        layout.addWidget(QLabel(
            "Importe el Excel que el Abogado capturó y exportó, para marcar PROCEDE "
            "o NO PROCEDE en cada fila. Cada archivo importado queda separado -- "
            "elija abajo si quiere ver los pendientes de revisar o los ya revisados."
        ))

        abogado_row = QHBoxLayout()
        abogado_row.addWidget(QLabel("Abogado que capturó este archivo:"))
        self.abogado_combo = QComboBox()
        for abogado in users_repo.list_by_role(ROLE_ABOGADO):
            self.abogado_combo.addItem(f"{abogado.full_name} ({abogado.username})", abogado.id)
        abogado_row.addWidget(self.abogado_combo)
        layout.addLayout(abogado_row)

        import_revision_btn = QPushButton("Importar captura del Abogado")
        import_revision_btn.clicked.connect(self._on_import_revision)
        layout.addWidget(import_revision_btn)

        # Pantalla previa: se elige el ESTADO de revisión (Pendiente/Revisado)
        # y sólo entonces se listan los archivos importados en ese estado.
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Estado de revisión:"))
        self.estado_combo = QComboBox()
        for label, value in DOC_STATES:
            self.estado_combo.addItem(label, value)
        self.estado_combo.currentIndexChanged.connect(self._on_estado_changed)
        selector_row.addWidget(self.estado_combo)
        open_import_btn = QPushButton("Abrir")
        open_import_btn.clicked.connect(self._on_open_selected_import)
        selector_row.addWidget(open_import_btn)
        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self._on_clear)
        selector_row.addWidget(clear_btn)
        layout.addLayout(selector_row)

        self.available_list = QListWidget()
        self.available_list.setMaximumHeight(140)
        layout.addWidget(self.available_list)

        self.filename_label = QLabel(SIN_ARCHIVO_TEXT)
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        # Identidad del documento importado (UUID + hash embebidos en el
        # .mcdiep que exportó el Abogado) -- para comparar contra lo que
        # muestra el PDF físico que acompaña a ese mismo archivo.
        self.identity_label = QLabel()
        self.identity_label.setWordWrap(True)
        layout.addWidget(self.identity_label)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar por:"))
        self.revision_search_field_combo = QComboBox()
        for label in REVISION_SEARCH_COLUMNS:
            self.revision_search_field_combo.addItem(label, REVISION_SEARCH_COLUMNS[label])
        search_row.addWidget(self.revision_search_field_combo)
        self.revision_search_input = QLineEdit()
        self.revision_search_input.setPlaceholderText("Escriba para buscar y posicionarse en la fila...")
        self.revision_search_input.returnPressed.connect(self._on_search_revision)
        search_row.addWidget(self.revision_search_input)
        revision_search_btn = QPushButton("Buscar")
        revision_search_btn.clicked.connect(self._on_search_revision)
        search_row.addWidget(revision_search_btn)
        layout.addLayout(search_row)

        self.revision_table = QTableWidget(0, len(HEADERS_REVISION))
        self.revision_table.setHorizontalHeaderLabels(HEADERS_REVISION)
        self.revision_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.revision_table.horizontalHeader().setStretchLastSection(True)
        self.revision_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.revision_table)

        export_revision_btn = QPushButton("Exportar revisión (todo lo importado)")
        export_revision_btn.setProperty("role", "primary")
        export_revision_btn.clicked.connect(self._on_export_revision)
        layout.addWidget(export_revision_btn)

        self._refresh_available_list()

    # --- Archivos importados (pantalla previa) --------------------------------------
    def _refresh_available_list(self) -> None:
        self.available_list.clear()
        want_reviewed = self.estado_combo.currentData() == DOC_STATE_REVISADO
        for imp in revisiones_repo.list_revision_imports(self.agente_user.id):
            if imp.is_reviewed != want_reviewed:
                continue
            label = (
                f"{imp.source_filename} — {imp.reviewed_rows}/{imp.total_rows} revisadas — "
                f"{format_local_datetime(imp.imported_at)}"
            )
            item = QListWidgetItem(label)
            item.setData(1000, imp.id)
            self.available_list.addItem(item)

    def _on_estado_changed(self) -> None:
        self._refresh_available_list()

    def _on_open_selected_import(self) -> None:
        item = self.available_list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "Nada seleccionado", "Seleccione un archivo de la lista primero."
            )
            return
        self._load_import(item.data(1000))

    def _load_import(self, revision_import_id: int) -> None:
        self._current_import_id = revision_import_id
        rows = revisiones_repo.list_revision_rows_for_import(revision_import_id)
        filename = rows[0].source_filename if rows else None
        self.filename_label.setText(f"Archivo en revisión: {filename}" if filename else SIN_ARCHIVO_TEXT)
        self.archivo_cambiado.emit(filename or "")

        imp = revisiones_repo.get_revision_import(revision_import_id)
        if imp is not None and imp.imported_uuid:
            self.identity_label.setText(
                f"Documento recibido del Abogado — UUID: {imp.imported_uuid}  Hash: {imp.imported_hash}"
            )
        else:
            self.identity_label.setText("")

        self._refresh_revision_table(rows)

    def _on_clear(self) -> None:
        self.available_list.clear()
        self._current_import_id = None
        self.filename_label.setText(SIN_ARCHIVO_TEXT)
        self.identity_label.setText("")
        self.archivo_cambiado.emit("")
        self._refresh_revision_table([])

    # --- Importar ------------------------------------------------------------------
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
            result = parse_abogado_export_file(Path(file_path))
        except McdiepVerificationError as exc:
            QMessageBox.critical(self, "No se pudo abrir el archivo", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if not result.rows:
            QMessageBox.warning(self, "Archivo vacío", "No se encontraron filas de datos en el archivo.")
            return

        abogado_id = self.abogado_combo.currentData()
        abogado = users_repo.get_by_id(abogado_id) if abogado_id else None
        filename = Path(file_path).name
        abogado_nombre = abogado.full_name if abogado else None

        revision_import_id = revisiones_repo.create_revision_import(
            agente_id=self.agente_user.id, source_filename=filename,
            abogado_nombre=abogado_nombre, abogado_id=abogado_id,
            imported_uuid=result.document_uuid, imported_hash=result.file_hash,
        )
        revisiones_repo.add_revision_rows(
            agente_id=self.agente_user.id, revision_import_id=revision_import_id,
            source_filename=filename, abogado_nombre=abogado_nombre, abogado_id=abogado_id,
            rows=result.rows,
        )

        self.estado_combo.setCurrentIndex(self.estado_combo.findData(DOC_STATE_PENDIENTE))
        self._refresh_available_list()
        self._load_import(revision_import_id)
        for row in range(self.available_list.count()):
            if self.available_list.item(row).data(1000) == revision_import_id:
                self.available_list.setCurrentRow(row)
                break

        QMessageBox.information(
            self, "Importado",
            f"Se importaron {len(result.rows)} filas para revisión.\n\n"
            f"UUID: {result.document_uuid}\nHash: {result.file_hash}",
        )

    # --- Tabla de revisión -----------------------------------------------------------
    def _refresh_revision_table(self, rows: list[revisiones_repo.RevisionRowMandamiento]) -> None:
        self.revision_table.setUpdatesEnabled(False)
        try:
            self.revision_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                values = [
                    row.folio, row.cta_predial, row.contribuyente,
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
                self.revision_table.setCellWidget(r, len(values), procede_combo)

                id_item = QTableWidgetItem(str(row.abogado_id) if row.abogado_id else "")
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.revision_table.setItem(r, len(values) + 1, id_item)
        finally:
            self.revision_table.setUpdatesEnabled(True)

    def _flash_highlight_revision(self, row_index: int, columns: tuple[int, ...]) -> None:
        original_colors = []
        for col in columns:
            item = self.revision_table.item(row_index, col)
            original_colors.append(item.background())
            item.setBackground(HIGHLIGHT_COLOR)

        def revert():
            for col, color in zip(columns, original_colors):
                item = self.revision_table.item(row_index, col)
                if item is not None:
                    item.setBackground(color)

        QTimer.singleShot(1000, revert)

    def _on_search_revision(self) -> None:
        text = self.revision_search_input.text().strip().lower()
        if not text:
            return

        col = self.revision_search_field_combo.currentData()
        for row_index in range(self.revision_table.rowCount()):
            item = self.revision_table.item(row_index, col)
            if item is not None and text in item.text().lower():
                self.revision_table.scrollToItem(item)
                self.revision_table.selectRow(row_index)
                self._flash_highlight_revision(row_index, tuple(REVISION_SEARCH_COLUMNS.values()))
                return

        QMessageBox.information(self, "Sin resultados", "No se encontró ninguna fila que coincida con la búsqueda.")

    def _on_procede_changed(self, row_id: int, combo: QComboBox) -> None:
        if self.simulate:
            return
        revisiones_repo.update_revision_procede(row_id, combo.currentData())
        self._refresh_available_list()

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
        output_path = exports_dir() / f"REVISION MANDAMIENTOS DEL {fecha}.xlsx"
        export_revision(rows, output_path)
        QMessageBox.information(self, "Exportado", f"Archivo exportado:\n{output_path}")
