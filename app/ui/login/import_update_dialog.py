"""Importar el paquete de actualización de credenciales que envió el Administrador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from app.auth import recovery


class ImportUpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar actualización del Administrador")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seleccione el archivo de actualización (.json) que le envió el "
                "Administrador después de resolver su solicitud."
            )
        )
        select_btn = QPushButton("Seleccionar archivo de actualización")
        select_btn.clicked.connect(self._on_select)
        layout.addWidget(select_btn)

    def _on_select(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar paquete de actualización", "", "JSON (*.json)")
        if not file_path:
            return
        try:
            payload = recovery.load_json_file(Path(file_path))
            message = recovery.apply_update_package(payload)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al aplicar la actualización", str(exc))
            return

        QMessageBox.information(self, "Actualización aplicada", message)
        self.accept()
