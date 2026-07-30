"""Punto de entrada del Sistema PAE."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.auth import first_run, session
from app.db.migrations import ensure_schema
from app.ui.login.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.widgets.styles import apply_app_icon
from app.update.flow import run_update_check


def main() -> int:
    app = QApplication(sys.argv)
    ensure_schema()
    apply_app_icon(app)

    try:
        first_run.ensure_seed_accounts()
    except first_run.SeedFileMissingError as exc:
        QMessageBox.critical(None, "Error de instalación", str(exc))
        return 1

    while True:
        login = LoginWindow()
        if login.exec() != QDialog.DialogCode.Accepted:
            return 0

        user = session.current()
        if user is None:
            continue

        run_update_check(None)  # tras login exitoso, para cualquier rol; nunca bloquea el flujo normal

        window = MainWindow(user)
        window.show()
        app.exec()

        if session.current() is None:
            # Se cerró sesión: volver a mostrar el login.
            continue
        return 0


if __name__ == "__main__":
    sys.exit(main())
