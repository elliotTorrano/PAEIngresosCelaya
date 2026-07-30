"""Consulta el último release público de GitHub y compara versiones.

Como el programa es offline por diseño, este chequeo debe poder fallar de
cualquier forma (sin internet, DNS, timeout, JSON inválido, límite de la API,
release sin el asset esperado) sin nunca interrumpir el arranque normal:
check_for_update() atrapa toda excepción y devuelve None en vez de propagarla.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

# Repositorio público donde se publican los releases del programa. Si el
# repositorio cambia de nombre o dueño, sólo hay que editar esta constante.
GITHUB_REPO = "elliotTorrano/PAEIngresosCelaya"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Nombre exacto (sensible a mayúsculas) que debe llevar el asset del .exe en
# cada release de GitHub para que el programa lo reconozca.
ASSET_NAME = "SistemaPAE.exe"

REQUEST_TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.6.0' o '0.6.0' -> (0, 6, 0). Lanza ValueError si no es numérico."""
    cleaned = text.strip()
    if cleaned[:1] in ("v", "V"):
        cleaned = cleaned[1:]
    parts = cleaned.split(".")
    if not parts:
        raise ValueError(f"Versión vacía: {text!r}")
    return tuple(int(part) for part in parts)


def is_newer(current: str, candidate: str) -> bool:
    """True si candidate es una versión más nueva que current. Nunca lanza
    excepciones: un tag mal formado simplemente no cuenta como más nuevo."""
    try:
        return parse_version(candidate) > parse_version(current)
    except (ValueError, AttributeError):
        return False


def check_for_update(current_version: str) -> UpdateInfo | None:
    """Consulta el último release en GitHub. Devuelve None ante cualquier
    problema (sin conexión, timeout, JSON inválido, sin release más nuevo,
    o release nuevo sin el asset SistemaPAE.exe)."""
    try:
        request = urllib.request.Request(
            RELEASES_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SistemaPAE-UpdateChecker",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.load(response)

        tag = data.get("tag_name", "")
        if not is_newer(current_version, tag):
            return None

        for asset in data.get("assets", []):
            if asset.get("name") == ASSET_NAME:
                download_url = asset.get("browser_download_url")
                if not download_url:
                    return None
                version = tag[1:] if tag[:1] in ("v", "V") else tag
                return UpdateInfo(version=version, download_url=download_url)
        return None
    except Exception:
        return None
