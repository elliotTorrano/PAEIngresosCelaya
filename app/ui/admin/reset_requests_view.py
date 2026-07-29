"""El Administrador importa la solicitud de un usuario y genera el paquete de respuesta."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
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

from app.auth import recovery
from app.auth.passwords import hash_password
from app.config import CERT_ROLES, RESET_REASON_LABELS
from app.db.repositories import reset_requests as reset_requests_repo
from app.db.repositories.users import User
from app.utils.paths import reset_requests_dir


class ResetRequestsView(QWidget):
    def __init__(self, admin_user: User, parent=None):
        super().__init__(parent)
        self.admin_user = admin_user
        self._current_payload: dict | None = None
        self._current_request_id: int | None = None

        layout = QVBoxLayout(self)

        import_btn = QPushButton("Importar solicitud (.json) recibida por correo")
        import_btn.clicked.connect(self._on_import)
        layout.addWidget(import_btn)

        self.detail_box = QGroupBox("Solicitud seleccionada")
        detail_layout = QVBoxLayout(self.detail_box)
        self.detail_label = QLabel("(ninguna solicitud importada)")
        self.detail_label.setWordWrap(True)
        detail_layout.addWidget(self.detail_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Nueva contraseña (sólo Abogados)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        detail_layout.addWidget(self.password_input)

        self.resolve_btn = QPushButton("Resolver y generar paquete de actualización")
        self.resolve_btn.clicked.connect(self._on_resolve)
        self.resolve_btn.setEnabled(False)
        detail_layout.addWidget(self.resolve_btn)

        layout.addWidget(self.detail_box)

        layout.addWidget(QLabel("Solicitudes pendientes registradas en esta instalación:"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Usuario", "Rol", "Motivo", "Fecha"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        for r in reset_requests_repo.list_pending():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r["username"]))
            self.table.setItem(row, 1, QTableWidgetItem(r["role"]))
            self.table.setItem(row, 2, QTableWidgetItem(RESET_REASON_LABELS.get(r["reason"], r["reason"])))
            self.table.setItem(row, 3, QTableWidgetItem(r["requested_at"]))

    def _on_import(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar solicitud", "", "JSON (*.json)")
        if not file_path:
            return
        try:
            payload = recovery.load_json_file(Path(file_path))
            if payload.get("type") != "reset_request":
                raise ValueError("El archivo no es una solicitud de cambio de contraseña/certificado válida.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Archivo inválido", str(exc))
            return

        self._current_payload = payload
        self._current_request_id = reset_requests_repo.create(
            username=payload["username"], role=payload["role"], reason=payload["reason"],
            detail=payload.get("detail"), request_file_path=file_path,
        )
        self.detail_label.setText(
            f"Usuario: {payload['username']} ({payload.get('full_name', '')})\n"
            f"Rol: {payload['role']}\n"
            f"Motivo: {RESET_REASON_LABELS.get(payload['reason'], payload['reason'])}\n"
            f"Detalle: {payload.get('detail') or '(sin detalle)'}\n"
            f"Solicitado: {payload.get('requested_at', '')}"
        )
        self.password_input.setVisible(payload["role"] not in CERT_ROLES)
        self.resolve_btn.setEnabled(True)
        self._refresh_table()

    def _on_resolve(self) -> None:
        payload = self._current_payload
        if payload is None:
            return

        if payload["role"] in CERT_ROLES:
            package = recovery.build_update_package_allow_reenroll(
                username=payload["username"], role=payload["role"], admin_username=self.admin_user.username,
            )
        else:
            password = self.password_input.text()
            if len(password) < 6:
                QMessageBox.warning(self, "Contraseña inválida", "La nueva contraseña debe tener al menos 6 caracteres.")
                return
            pwd_hash, salt = hash_password(password)
            package = recovery.build_update_package_set_password(
                username=payload["username"], role=payload["role"],
                password_hash=pwd_hash, password_salt=salt, admin_username=self.admin_user.username,
            )

        folder = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta para guardar el paquete de actualización", str(reset_requests_dir())
        )
        if not folder:
            return

        package_path = recovery.save_update_package(package, Path(folder))
        if self._current_request_id is not None:
            reset_requests_repo.mark_attended(self._current_request_id)

        QMessageBox.information(
            self, "Paquete generado",
            f"Se guardó en:\n{package_path}\n\nHágaselo llegar al solicitante para que lo importe "
            "en su propia instalación (opción 'Importar actualización del administrador' en el login).",
        )

        self._current_payload = None
        self._current_request_id = None
        self.detail_label.setText("(ninguna solicitud importada)")
        self.password_input.clear()
        self.resolve_btn.setEnabled(False)
        self._refresh_table()
