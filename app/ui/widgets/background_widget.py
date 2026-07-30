"""Widget que pinta una imagen de fondo preservando su proporción (sin
recortarla ni deformarla) y sin fijar ningún tamaño propio -- a diferencia
del QSS `border-image`, que se usaba antes y estiraba la imagen sin
respetar el aspecto."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

DEFAULT_COLOR = "#f4f6f8"


class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._color = QColor(DEFAULT_COLOR)

    def set_image_path(self, path: Path | None) -> None:
        if path is not None and path.exists():
            pixmap = QPixmap(str(path))
            self._pixmap = pixmap if not pixmap.isNull() else None
        else:
            self._pixmap = None
        self.update()

    def set_color(self, color_hex: str | None) -> None:
        self._color = QColor(color_hex) if color_hex else QColor(DEFAULT_COLOR)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)
        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)
