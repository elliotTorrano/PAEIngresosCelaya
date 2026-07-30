"""Orquestación de la actualización automática: única pieza de app/update que
toca Qt. Se llama una vez justo después de un inicio de sesión exitoso, para
cualquier rol; ninguna falla aquí debe impedir que el programa siga su curso
normal."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from app.__version__ import __version__
from app.config import APP_NAME
from app.update import checker, installer
from app.utils import paths


def run_update_check(parent: QWidget | None) -> None:
    try:
        info = checker.check_for_update(__version__)
        if info is None:
            return

        answer = QMessageBox.question(
            parent,
            "Actualización disponible",
            f"Hay una nueva versión {info.version} de {APP_NAME} disponible "
            f"(tienes la {__version__}).\n\n"
            "¿Deseas instalarla ahora? El programa se cerrará y se volverá a "
            "abrir automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        updater_exe = paths.updater_exe_path()
        if not updater_exe.exists():
            QMessageBox.warning(
                parent,
                "No se pudo actualizar",
                "No se encontró updater.exe junto al programa, así que esta "
                "instalación no puede actualizarse sola todavía. Esto es "
                "normal si esta copia viene de una versión anterior a la "
                "0.6.0: actualízala una vez de forma manual (copiando la "
                "carpeta más reciente) y, de ahí en adelante, se actualizará "
                "sola.",
            )
            return

        dest = paths.update_dir() / "SistemaPAE_nuevo.exe"
        progress = QProgressDialog("Descargando actualización...", "Cancelar", 0, 100, parent)
        progress.setWindowTitle("Actualizando")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        cancelled = False

        def on_progress(read: int, total: int) -> None:
            if total > 0:
                progress.setValue(min(int(read * 100 / total), 100))
            if progress.wasCanceled():
                raise RuntimeError("Descarga cancelada por el usuario")

        download_failed = False
        try:
            installer.download_update(info.download_url, dest, on_progress)
        except RuntimeError:
            cancelled = True
        except Exception:
            download_failed = True
        finally:
            progress.close()

        if cancelled or download_failed:
            _cleanup_partial_download(dest)
            if download_failed:
                QMessageBox.warning(
                    parent,
                    "No se pudo actualizar",
                    "Ocurrió un problema al descargar la actualización. Se "
                    "continuará con la versión actual del programa.",
                )
            return

        installer.launch_updater_and_exit(updater_exe, paths.base_dir() / "SistemaPAE.exe", dest)
        # No hay código después de esta línea en un caso real: el proceso termina ahí.
    except Exception:
        pass  # defensa adicional: nada de esta función debe impedir el login normal


def _cleanup_partial_download(dest) -> None:
    dest.unlink(missing_ok=True)
    dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
