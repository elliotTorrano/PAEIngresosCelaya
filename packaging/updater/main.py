"""updater.exe -- reemplaza SistemaPAE.exe con una versión nueva ya descargada,
y lo vuelve a abrir. Uso: updater.exe <ruta_exe_objetivo> <ruta_exe_nuevo>

Deliberadamente no importa PySide6 ni el paquete app: debe ser un binario
mínimo e independiente, que no pueda fallar por errores ajenos al programa
principal. Se ejecuta después de que SistemaPAE.exe ya terminó, para poder
sobrescribirlo (un .exe en ejecución no puede reemplazarse a sí mismo en
Windows).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

RETRY_SECONDS = 15
RETRY_INTERVAL = 0.5


def main() -> int:
    if len(sys.argv) != 3:
        return 1

    target, new = sys.argv[1], sys.argv[2]

    deadline = time.time() + RETRY_SECONDS
    replaced = False
    while time.time() < deadline:
        try:
            os.replace(new, target)
            replaced = True
            break
        except (PermissionError, OSError):
            # El archivo objetivo puede seguir bloqueado un momento mientras
            # el proceso anterior termina de cerrarse; se reintenta.
            time.sleep(RETRY_INTERVAL)

    if not replaced:
        return 1

    try:
        os.rmdir(os.path.dirname(new))
    except OSError:
        pass  # la carpeta no estaba vacía o ya no existe; no es un error

    subprocess.Popen([target], close_fds=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
