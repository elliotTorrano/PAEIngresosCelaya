"""Paleta de colores configurable del programa: identidad (verde de fábrica),
crítico (guinda de fábrica -- acciones importantes y encabezados de tabla) y
estructura (ocre de fábrica -- bordes/separadores).

Hay DOS paletas persistidas, independientes entre sí:
- La de interfaz (saved_colors/save_as_default): pinta menús, botones,
  pestañas -- puede ajustarse al gusto de quien use el programa en esa
  computadora.
- La del PDF (saved_pdf_colors/save_pdf_colors): sólo afecta el encabezado
  de tabla de los PDF exportados. Se guarda aparte a propósito -- un
  documento oficial no debe cambiar de color porque alguien ajustó la
  interfaz a su gusto; requiere su propia acción explícita de guardado.

Ambas se guardan en app_settings dentro de pae.db -- a diferencia de
resources/base_style.qss (que viaja empacado en el .exe y se reemplaza por
completo en cada actualización del programa), esto sobrevive cualquier
actualización. Ver app/ui/admin/color_settings_view.py para la pantalla que
las edita."""

from __future__ import annotations

import re
from string import Template

from app.db.repositories import settings as settings_repo
from app.utils.paths import resource_dir

DEFAULT_COLORS: dict[str, str] = {
    "identidad": "#3A6B46",
    "critico": "#8A1E2D",
    "estructura": "#A67242",
}

_SETTINGS_KEYS = {
    "identidad": settings_repo.KEY_THEME_IDENTITY,
    "critico": settings_repo.KEY_THEME_CRITICAL,
    "estructura": settings_repo.KEY_THEME_STRUCTURE,
}

_PDF_SETTINGS_KEYS = {
    "identidad": settings_repo.KEY_PDF_THEME_IDENTITY,
    "critico": settings_repo.KEY_PDF_THEME_CRITICAL,
    "estructura": settings_repo.KEY_PDF_THEME_STRUCTURE,
}

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Vista previa activa en esta sesión (sin persistir) -- ver set_preview_colors().
# None = no hay vista previa, se usan los colores guardados.
_preview: dict[str, str] | None = None


def is_valid_hex(value: str) -> bool:
    return bool(_HEX_RE.match(value.strip()))


def saved_colors() -> dict[str, str]:
    """Colores realmente guardados como predeterminados, ignorando cualquier
    vista previa activa -- lo que debe usar cualquier cosa que se archive de
    forma permanente (p. ej. el PDF exportado): un documento oficial nunca
    debe llevar un color que sólo se estaba probando y no se guardó."""
    return {
        role: settings_repo.get(key) or DEFAULT_COLORS[role]
        for role, key in _SETTINGS_KEYS.items()
    }


def current_colors() -> dict[str, str]:
    """Colores activos para la interfaz en pantalla ahora mismo: la vista
    previa si hay una activa: si no, los guardados."""
    return _preview if _preview is not None else saved_colors()


def set_preview_colors(colors: dict[str, str] | None) -> None:
    """Activa (o, con None, apaga) una vista previa de sesión -- no toca lo
    guardado en la base. Después de llamar esto hay que refrescar las
    ventanas abiertas para que se note (ver refresh_all_windows_theme en
    app/ui/widgets/styles.py)."""
    global _preview
    _preview = dict(colors) if colors is not None else None


def save_as_default(colors: dict[str, str]) -> None:
    """Guarda `colors` como los nuevos predeterminados de INTERFAZ
    (persistente, ver docstring del módulo) y apaga cualquier vista previa
    activa -- a partir de aquí lo guardado y lo mostrado son lo mismo. No
    toca la paleta del PDF -- ver save_pdf_colors()."""
    for role, key in _SETTINGS_KEYS.items():
        settings_repo.set(key, colors[role])
    set_preview_colors(None)


def saved_pdf_colors() -> dict[str, str]:
    """Colores guardados para el PDF -- independientes de los de interfaz.
    Lo único que hoy usa esto es el encabezado de tabla (rol 'critico')."""
    return {
        role: settings_repo.get(key) or DEFAULT_COLORS[role]
        for role, key in _PDF_SETTINGS_KEYS.items()
    }


def save_pdf_colors(colors: dict[str, str]) -> None:
    """Guarda `colors` como los nuevos predeterminados del PDF
    (persistente). No afecta la interfaz -- ver save_as_default()."""
    for role, key in _PDF_SETTINGS_KEYS.items():
        settings_repo.set(key, colors[role])


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _lighten(value: str, ratio: float) -> str:
    r, g, b = _hex_to_rgb(value)
    return _rgb_to_hex((r + (255 - r) * ratio, g + (255 - g) * ratio, b + (255 - b) * ratio))


def _darken(value: str, ratio: float) -> str:
    r, g, b = _hex_to_rgb(value)
    return _rgb_to_hex((r * (1 - ratio), g * (1 - ratio), b * (1 - ratio)))


def _derive_tokens(colors: dict[str, str]) -> dict[str, str]:
    """A partir de los 3 colores base, deriva los tonos que usa la plantilla
    de resources/base_style.qss (fondos suaves, texto legible, estados hover/
    pressed) -- mismas proporciones sin importar qué combinación se
    configure, no sólo la de fábrica."""
    tokens: dict[str, str] = {}
    for role, base in colors.items():
        tokens[role] = base
        tokens[f"{role}_wash"] = _lighten(base, 0.88)
        tokens[f"{role}_soft"] = _lighten(base, 0.55)
        tokens[f"{role}_texto"] = _darken(base, 0.35)
        tokens[f"{role}_hover"] = _darken(base, 0.15)
        tokens[f"{role}_press"] = _darken(base, 0.30)
        tokens[f"{role}_on"] = _lighten(base, 0.90)
    return tokens


def render_qss() -> str:
    """Lee la plantilla resources/base_style.qss y sustituye los marcadores
    $identidad/$critico/$estructura (y variantes) con los colores activos
    ahora mismo (vista previa o guardados)."""
    path = resource_dir() / "base_style.qss"
    if not path.exists():
        return ""
    template = Template(path.read_text(encoding="utf-8"))
    return template.substitute(_derive_tokens(current_colors()))
