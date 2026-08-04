"""Repositorio de configuración clave/valor (apariencia: ícono, fondo y
paleta de colores). Vive en app_settings dentro de pae.db -- a diferencia de
resources/base_style.qss (que viaja dentro del .exe y se reemplaza por
completo en cada actualización), lo que se guarda aquí sobrevive cualquier
actualización del programa."""

from __future__ import annotations

from app.db.connection import get_connection

KEY_ICON_PATH = "icon_path"
KEY_BACKGROUND_PATH = "background_path"
KEY_BACKGROUND_COLOR = "background_color"
KEY_THEME_IDENTITY = "theme_color_identity"
KEY_THEME_CRITICAL = "theme_color_critical"
KEY_THEME_STRUCTURE = "theme_color_structure"
# Paleta independiente para el PDF -- un documento oficial no debe cambiar de
# color sólo porque un agente ajustó la interfaz a su gusto. Ver
# app/ui/widgets/theme.py::saved_pdf_colors().
KEY_PDF_THEME_IDENTITY = "pdf_color_identity"
KEY_PDF_THEME_CRITICAL = "pdf_color_critical"
KEY_PDF_THEME_STRUCTURE = "pdf_color_structure"
# Ruta del archivo .xlsx maestro del reporte general del Reporteador --
# se regenera por completo (desde la base de datos) cada vez que el reporte
# cambia. Ver app/ui/reporteador/reporte_requerimientos_view.py.
KEY_REPORTE_REQUERIMIENTOS_EXCEL_PATH = "reporte_requerimientos_excel_path"
KEY_REPORTE_MANDAMIENTOS_EXCEL_PATH = "reporte_mandamientos_excel_path"


def get(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set(key: str, value: str | None) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()
