"""Contenedor del "Reporte General" del Reporteador: una pestaña por tipo de
documento, igual que app/ui/widgets/historico_view.py."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.ui.reporteador.reporte_mandamientos_view import ReporteMandamientosView
from app.ui.reporteador.reporte_requerimientos_view import ReporteRequerimientosView


class ReporteGeneralView(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user

        layout = QVBoxLayout(self)

        self.tab_requerimientos = ReporteRequerimientosView(user)
        self.tab_mandamientos = ReporteMandamientosView(user)

        tabs = QTabWidget()
        tabs.addTab(self.tab_requerimientos, "Requerimiento")
        tabs.addTab(self.tab_mandamientos, "Mandamiento")
        layout.addWidget(tabs)
