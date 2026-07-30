"""Descarga del .exe nuevo y entrega a updater.exe (que hace el reemplazo real).

Un .exe en ejecución no puede sobrescribirse a sí mismo en Windows, por eso el
reemplazo lo hace un ayudante externo (updater.exe) que arranca después de que
este proceso termina.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable

CHUNK_SIZE = 262_144  # 256 KiB

# Flags de Windows para que updater.exe quede desvinculado de este proceso:
# sigue vivo aunque este proceso termine justo después de lanzarlo.
_DETACHED_FLAGS = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
)


def download_update(
    url: str,
    destination: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """Descarga en streaming a un archivo temporal ".part" y sólo lo
    renombra al destino final si terminó completo. Puede lanzar excepciones:
    quien la llama ya avisó al usuario que va a intentar actualizar."""
    request = urllib.request.Request(url, headers={"User-Agent": "SistemaPAE-UpdateChecker"})
    tmp_path = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=15) as response:
        total = int(response.headers.get("Content-Length", -1))
        read = 0
        with open(tmp_path, "wb") as f:
            while chunk := response.read(CHUNK_SIZE):
                f.write(chunk)
                read += len(chunk)
                if progress_callback:
                    progress_callback(read, total)
    tmp_path.replace(destination)


def launch_updater_and_exit(updater_exe: Path, target_exe: Path, new_exe: Path) -> None:
    """Lanza updater.exe (desvinculado) y termina este proceso de inmediato."""
    subprocess.Popen(
        [str(updater_exe), str(target_exe), str(new_exe)],
        creationflags=_DETACHED_FLAGS,
        close_fds=True,
    )
    os._exit(0)  # nunca sys.exit(): evita que Qt intente limpiar widgets a medio cerrar
