"""Personalización de la paleta de colores del programa. Tres colores base:
identidad (uso diario), crítico (acciones importantes + encabezados de
tabla) y estructura (bordes).

Accesible para Administrador/Súper-usuario (interfaz + PDF, permanente en
'Colores') y para el Agente del PAE (sólo interfaz, en el menú 'Otros' --
ver `allow_pdf`). El Abogado no tiene acceso: siempre se queda con lo que
haya quedado guardado, sin poder cambiarlo -- ver
app/ui/main_window.py::_build_otros_menu.

La interfaz y el PDF se guardan por separado a propósito: la interfaz puede
ajustarse al gusto de quien use el programa en esa computadora, pero el PDF
es un documento oficial y sólo debe cambiar cuando alguien con acceso al PDF
lo decida explícitamente con su propio botón. Ver app/ui/widgets/theme.py
para cómo se derivan los tonos y se guardan/aplican."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.db.repositories.users import User
from app.ui.widgets import theme
from app.ui.widgets.styles import refresh_all_windows_theme

ROLE_ORDER = ("identidad", "critico", "estructura")
ROLE_LABELS = {
    "identidad": "Identidad (menús, pestañas, botones de uso diario)",
    "critico": "Crítico (Exportar/Firmar, encabezados de tabla y del PDF -- se guardan por separado)",
    "estructura": "Estructura (bordes y separadores)",
}
_SWATCH_BASE_STYLE = "border: 1px solid #999; border-radius: 3px;"


class ColorSettingsView(QWidget):
    def __init__(self, user: User, parent=None, allow_pdf: bool = True):
        super().__init__(parent)
        self.user = user
        self.allow_pdf = allow_pdf
        self._swatches: dict[str, QLabel] = {}
        self._inputs: dict[str, QLineEdit] = {}

        layout = QVBoxLayout(self)
        if allow_pdf:
            intro = (
                "Personalice los 3 colores base del programa (formato #RRGGBB). "
                "'Aplicar' los prueba de inmediato en TODAS las ventanas abiertas "
                "para poder revisarlos visualmente, sin guardar nada todavía -- se "
                "pierden al reiniciar el programa si no se guardan.\n\n"
                "La interfaz y el PDF se guardan POR SEPARADO a propósito: la "
                "interfaz puede ajustarse al gusto (menús, botones, pestañas), pero "
                "el PDF es un documento oficial y sólo debe cambiar cuando se "
                "decida explícitamente. 'Guardar cambios de interfaz' deja fijos "
                "los colores de pantalla; 'Guardar cambios del PDF' deja fijo el "
                "color del encabezado de los PDF exportados. Ambos se mantienen "
                "incluso después de actualizar el programa."
            )
        else:
            intro = (
                "Personalice a su gusto los 3 colores base de SU interfaz "
                "(formato #RRGGBB) -- menús, botones, pestañas. 'Aplicar' los "
                "prueba de inmediato en todas las ventanas abiertas, sin guardar "
                "nada todavía. 'Guardar cambios de interfaz' los deja fijos, "
                "incluso después de reiniciar o actualizar el programa.\n\n"
                "Esto NO afecta el color de los PDF que exporte -- ese color lo "
                "define el Administrador y es el mismo para todos, sin importar "
                "los colores que use aquí en pantalla."
            )
        layout.addWidget(QLabel(intro))

        for role in ROLE_ORDER:
            row = QHBoxLayout()
            row.addWidget(QLabel(ROLE_LABELS[role]))
            field = QLineEdit()
            field.setPlaceholderText("#RRGGBB")
            field.setMaximumWidth(110)
            field.textChanged.connect(lambda text, r=role: self._on_field_changed(r, text))
            row.addWidget(field)
            swatch = QLabel()
            swatch.setFixedSize(28, 20)
            swatch.setStyleSheet(_SWATCH_BASE_STYLE)
            row.addWidget(swatch)
            row.addStretch()
            layout.addLayout(row)
            self._inputs[role] = field
            self._swatches[role] = swatch

        self._load_current()

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Restaurar predeterminados")
        reset_btn.clicked.connect(self._on_reset_defaults)
        btn_row.addWidget(reset_btn)

        apply_btn = QPushButton("Aplicar (vista previa)")
        apply_btn.clicked.connect(self._on_apply_preview)
        btn_row.addWidget(apply_btn)

        save_interface_btn = QPushButton("Guardar cambios de interfaz")
        save_interface_btn.setProperty("role", "primary")
        save_interface_btn.clicked.connect(self._on_save_interface)
        btn_row.addWidget(save_interface_btn)

        if allow_pdf:
            save_pdf_btn = QPushButton("Guardar cambios del PDF")
            save_pdf_btn.setProperty("role", "primary")
            save_pdf_btn.clicked.connect(self._on_save_pdf)
            btn_row.addWidget(save_pdf_btn)
        layout.addLayout(btn_row)

        if allow_pdf:
            self._pdf_status_label = QLabel()
            layout.addWidget(self._pdf_status_label)
            self._refresh_pdf_status_label()

        layout.addStretch()

    def _load_current(self) -> None:
        colors = theme.current_colors()
        for role in ROLE_ORDER:
            self._inputs[role].setText(colors[role])

    def _on_field_changed(self, role: str, text: str) -> None:
        text = text.strip()
        if theme.is_valid_hex(text):
            self._swatches[role].setStyleSheet(f"background-color: {text}; {_SWATCH_BASE_STYLE}")
        else:
            self._swatches[role].setStyleSheet(f"background-color: transparent; {_SWATCH_BASE_STYLE}")

    def _collect_colors(self) -> dict[str, str] | None:
        colors: dict[str, str] = {}
        invalid: list[str] = []
        for role in ROLE_ORDER:
            text = self._inputs[role].text().strip()
            if theme.is_valid_hex(text):
                colors[role] = text.upper()
            else:
                invalid.append(ROLE_LABELS[role])
        if invalid:
            QMessageBox.warning(
                self, "Color inválido",
                "Escriba un color válido en formato #RRGGBB (ejemplo: #3A6B46) para:\n\n"
                + "\n".join(invalid),
            )
            return None
        return colors

    def _refresh_pdf_status_label(self) -> None:
        color = theme.saved_pdf_colors()["critico"]
        self._pdf_status_label.setText(
            f"Color actual guardado para el encabezado del PDF: {color}"
        )

    def _on_reset_defaults(self) -> None:
        for role in ROLE_ORDER:
            self._inputs[role].setText(theme.DEFAULT_COLORS[role])
        theme.set_preview_colors(dict(theme.DEFAULT_COLORS))
        refresh_all_windows_theme()
        QMessageBox.information(
            self, "Restaurado",
            "Se aplicaron los colores de fábrica en esta sesión (sólo interfaz). "
            "Si quiere que se mantengan aunque reinicie el programa, presione "
            "'Guardar cambios de interfaz'. Esto NO afecta el color del PDF -- "
            "para eso use 'Guardar cambios del PDF'.",
        )

    def _on_apply_preview(self) -> None:
        colors = self._collect_colors()
        if colors is None:
            return
        theme.set_preview_colors(colors)
        refresh_all_windows_theme()
        QMessageBox.information(
            self, "Vista previa aplicada",
            "Los colores se aplicaron a todas las ventanas abiertas para que los "
            "revise. Esto NO es permanente ni afecta al PDF: si no presiona "
            "'Guardar cambios de interfaz', se pierden en cuanto reinicie el "
            "programa.",
        )

    def _on_save_interface(self) -> None:
        colors = self._collect_colors()
        if colors is None:
            return

        proceed = QMessageBox.warning(
            self, "Guardar cambios de interfaz",
            "Esto cambiará el aspecto de TODA la interfaz del programa (menús, "
            "botones, pestañas) -- para todos los usuarios de esta computadora "
            "-- y la acción NO SE PUEDE DESHACER (a menos que vuelva a cambiar "
            "los colores manualmente después). El cambio se mantendrá aunque el "
            "programa se actualice. Esto NO afecta el color del PDF exportado.\n\n"
            "¿Confirma que quiere guardar estos colores como los nuevos "
            "predeterminados de interfaz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            return

        theme.save_as_default(colors)
        refresh_all_windows_theme()
        QMessageBox.information(
            self, "Guardado",
            "Los nuevos colores de interfaz quedaron guardados y ya se "
            "aplicaron en esta sesión. Se mantendrán en todas las ventanas, "
            "incluso después de reiniciar el programa o actualizarlo. El PDF no "
            "se vio afectado.",
        )

    def _on_save_pdf(self) -> None:
        colors = self._collect_colors()
        if colors is None:
            return

        proceed = QMessageBox.warning(
            self, "Guardar cambios del PDF",
            "Esto cambiará el color del encabezado de TODOS los PDF que se "
            "exporten de aquí en adelante (Requerimientos y Mandamientos), en "
            "esta computadora, y la acción NO SE PUEDE DESHACER (a menos que "
            "vuelva a cambiar el color manualmente después). El cambio se "
            "mantendrá aunque el programa se actualice. Esto NO afecta el color "
            "de la interfaz.\n\n¿Confirma que quiere guardar este color como el "
            "nuevo predeterminado del PDF?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            return

        theme.save_pdf_colors(colors)
        self._refresh_pdf_status_label()
        QMessageBox.information(
            self, "Guardado",
            "El nuevo color del PDF quedó guardado. Se usará en todos los PDF "
            "que se exporten de aquí en adelante, incluso después de reiniciar "
            "el programa o actualizarlo. La interfaz no se vio afectada.",
        )
