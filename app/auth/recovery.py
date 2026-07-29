"""Flujo de recuperación: solicitud del usuario -> revisión del admin -> paquete de actualización.

Como cada instalación tiene su propia base de datos aislada, un cambio que el
Administrador resuelve en su equipo no llega automáticamente al equipo de quien
lo solicitó. Se resuelve con el mismo patrón de "todo por archivo" que ya usa
el resto del programa:

1. El solicitante genera un archivo de solicitud (.json) y lo envía al admin.
2. El Administrador lo importa, resuelve el cambio en su base local, y genera
   un "paquete de actualización de credenciales" (.json) para regresar al solicitante.
3. El solicitante importa ese paquete en su propia instalación para aplicarlo.

No se transporta nunca una llave privada: para certificados, el paquete sólo
autoriza un nuevo enrolamiento (el usuario genera su propio par de llaves localmente).
"""

from __future__ import annotations

import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from app.config import ADMIN_NOTIFICATION_EMAIL_SUBJECT
from app.db.repositories import reset_requests as reset_requests_repo
from app.db.repositories import users as users_repo

ACTION_SET_PASSWORD = "set_password"
ACTION_ALLOW_REENROLL = "allow_reenroll"


# --- Lado del solicitante -----------------------------------------------------

def build_request_payload(*, username: str, role: str, full_name: str, reason: str, detail: str) -> dict:
    return {
        "type": "reset_request",
        "username": username,
        "role": role,
        "full_name": full_name,
        "reason": reason,
        "detail": detail,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


def save_request_file(payload: dict, folder: Path) -> Path:
    filename = f"solicitud_{payload['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = folder / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def register_local_request(payload: dict, request_file_path: Path) -> None:
    reset_requests_repo.create(
        username=payload["username"],
        role=payload["role"],
        reason=payload["reason"],
        detail=payload.get("detail"),
        request_file_path=str(request_file_path),
    )


def open_email_client(*, to_email: str, body: str, attachment_path: Path) -> bool:
    """Abre el correo dirigido al administrador. Devuelve True si el adjunto quedó
    puesto automáticamente (sólo posible con Outlook vía COM); False si el usuario
    debe adjuntar el archivo manualmente (mailto: no soporta adjuntos de forma
    confiable entre distintos clientes de correo)."""
    if sys.platform == "win32":
        try:
            import win32com.client  # type: ignore

            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.To = to_email
            mail.Subject = ADMIN_NOTIFICATION_EMAIL_SUBJECT
            mail.Body = body
            mail.Attachments.Add(str(attachment_path))
            mail.Display()
            return True
        except Exception:
            pass

    mailto = f"mailto:{to_email}?subject={quote(ADMIN_NOTIFICATION_EMAIL_SUBJECT)}&body={quote(body)}"
    webbrowser.open(mailto)
    return False


# --- Lado del administrador ----------------------------------------------------

def build_update_package_set_password(
    *, username: str, role: str, password_hash: str, password_salt: str, admin_username: str
) -> dict:
    return {
        "type": "credential_update",
        "action": ACTION_SET_PASSWORD,
        "username": username,
        "role": role,
        "password_hash": password_hash,
        "password_salt": password_salt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": admin_username,
    }


def build_update_package_allow_reenroll(*, username: str, role: str, admin_username: str) -> dict:
    return {
        "type": "credential_update",
        "action": ACTION_ALLOW_REENROLL,
        "username": username,
        "role": role,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": admin_username,
    }


def save_update_package(payload: dict, folder: Path) -> Path:
    filename = f"actualizacion_{payload['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = folder / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --- Aplicar el paquete en la instalación del solicitante ----------------------

def apply_update_package(payload: dict) -> str:
    """Aplica un paquete de actualización de credenciales a la base local.
    Devuelve un mensaje de confirmación para mostrar al usuario."""
    if payload.get("type") != "credential_update":
        raise ValueError("El archivo no es un paquete de actualización de credenciales válido.")

    user = users_repo.get_by_username(payload["username"])
    if user is None:
        raise ValueError(f"No existe el usuario '{payload['username']}' en esta instalación.")

    action = payload.get("action")
    if action == ACTION_SET_PASSWORD:
        users_repo.set_password(
            user.id, password_hash=payload["password_hash"], password_salt=payload["password_salt"]
        )
        return f"Se actualizó la contraseña de '{user.username}'. Ya puede iniciar sesión con la nueva."
    elif action == ACTION_ALLOW_REENROLL:
        users_repo.clear_certificate(user.id)
        return f"Se habilitó a '{user.username}' para generar un nuevo certificado en su siguiente inicio de sesión."
    else:
        raise ValueError(f"Acción de actualización desconocida: {action}")
