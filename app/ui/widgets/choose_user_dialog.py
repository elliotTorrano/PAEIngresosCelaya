"""Diálogo para que el Súper-usuario elija un Agente del PAE o Abogado cuya
pantalla quiere ver (modo simulación, ver MainWindow._on_choose_view_as)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.config import ROLE_ABOGADO, ROLE_AGENTE_PAE, ROLE_LABELS
from app.db.repositories import users as users_repo


class ChooseUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ver como...")
        self.selected_user: users_repo.User | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Elige un Agente del PAE o Abogado para ver su pantalla. Es sólo una "
            "simulación: no se guarda nada de lo que hagas ahí."
        ))

        self.list_widget = QListWidget()
        candidates = users_repo.list_by_role(ROLE_AGENTE_PAE) + users_repo.list_by_role(ROLE_ABOGADO)
        for candidate in candidates:
            item = QListWidgetItem(f"{candidate.full_name} ({ROLE_LABELS[candidate.role]}) — {candidate.username}")
            item.setData(Qt.ItemDataRole.UserRole, candidate.id)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        if not candidates:
            layout.addWidget(QLabel("No hay Agentes del PAE ni Abogados dados de alta todavía."))

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Ver")
        ok_btn.clicked.connect(self._on_accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_accept(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(self, "Elige uno", "Selecciona un usuario de la lista.")
            return
        user_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_user = users_repo.get_by_id(user_id)
        self.accept()
