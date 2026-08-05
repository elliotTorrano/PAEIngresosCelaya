"""Punto de entrada del Sistema PAE."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.auth import dummy_accounts, first_run, session
from app.db.migrations import ensure_schema
from app.sync.user_directory import pull_and_apply
from app.ui.login.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.widgets.styles import apply_app_icon
from app.update.flow import run_update_check
from app.utils.paths import data_dir


def _install_exception_hook() -> None:
    """Sin esto, un error dentro de un clic (una señal de Qt) se imprime a
    stderr y punto -- invisible en el .exe empacado (console=False), así que
    para quien usa el programa "no pasa nada" al hacer clic. Ahora se
    registra en data/error.log y se avisa en pantalla."""

    def _hook(exc_type, exc_value, exc_tb) -> None:
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_path = data_dir() / "error.log"
        try:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(f"\n--- {datetime.now().isoformat()} ---\n{detail}")
        except OSError:
            pass
        QMessageBox.critical(
            None, "Error inesperado",
            "Ocurrió un error inesperado y la última acción no se completó.\n\n"
            f"{exc_type.__name__}: {exc_value}\n\n"
            f"El detalle completo se guardó en:\n{log_path}",
        )

    sys.excepthook = _hook


def main() -> int:
    _install_exception_hook()
    app = QApplication(sys.argv)
    ensure_schema()
    apply_app_icon(app)

    try:
        first_run.ensure_seed_accounts()
    except first_run.SeedFileMissingError as exc:
        QMessageBox.critical(None, "Error de instalación", str(exc))
        return 1

    dummy_accounts.ensure_dummy_accounts()

    # Antes de pedir login: si hay una versión más nueva, se ofrece instalarla
    # primero (si el usuario acepta, el proceso termina aquí y updater.exe
    # reabre la versión nueva). Así nadie llega a autenticarse -- ni, para el
    # súper-usuario/Administrador, a enrolar un certificado -- contra una
    # versión ya desactualizada.
    run_update_check(None)

    # Igual de silencioso y best-effort que run_update_check: si no hay
    # internet o el directorio remoto no responde, no pasa nada -- las
    # cuentas dadas de alta desde otra instalación simplemente aparecerán
    # en el siguiente arranque con conexión.
    pull_and_apply()

    while True:
        login = LoginWindow()
        if login.exec() != QDialog.DialogCode.Accepted:
            return 0

        user = session.current()
        if user is None:
            continue

        window = MainWindow(user)
        window.show()
        app.exec()

        if session.current() is None:
            # Se cerró sesión: volver a mostrar el login.
            continue
        return 0


if __name__ == "__main__":
    sys.exit(main())
