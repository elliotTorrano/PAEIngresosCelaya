"""Repositorio de configuración clave/valor (apariencia: ícono y fondo)."""

from __future__ import annotations

from app.db.connection import get_connection

KEY_ICON_PATH = "icon_path"
KEY_BACKGROUND_PATH = "background_path"
KEY_BACKGROUND_COLOR = "background_color"


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
