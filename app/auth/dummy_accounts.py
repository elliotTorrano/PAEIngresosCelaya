"""Alta automática de las cuentas de prueba 'agente_dummy' y 'abogado_dummy'
para el piloto alpha con usuarios finales -- ver app/config.py::DUMMY_USERNAMES.

Se siembran igual que el súper-usuario/Administrador (ver
app/auth/first_run.py): de forma determinista, en cualquier instalación, sin
pedirse de forma interactiva. A diferencia de esas cuentas, no dependen del
archivo de sembrado cifrado -- usan una contraseña fija conocida
(DUMMY_PASSWORD) para que cualquier persona que haga la prueba pueda entrar
sin necesitar un certificado ni que alguien más la dé de alta."""

from __future__ import annotations

from app.auth.passwords import hash_password
from app.config import (
    AUTH_TYPE_PASSWORD,
    DUMMY_ABOGADO_USERNAME,
    DUMMY_AGENTE_USERNAME,
    DUMMY_PASSWORD,
    ROLE_ABOGADO,
    ROLE_AGENTE_PAE,
)
from app.db.repositories import users as users_repo


def ensure_dummy_accounts() -> None:
    """Crea agente_dummy y abogado_dummy si todavía no existen localmente.
    Idempotente: en instalaciones ya sembradas no hace nada."""
    _ensure_dummy(DUMMY_AGENTE_USERNAME, ROLE_AGENTE_PAE, "Agente del PAE (prueba)")
    _ensure_dummy(DUMMY_ABOGADO_USERNAME, ROLE_ABOGADO, "Abogado (prueba)")


def _ensure_dummy(username: str, role: str, full_name: str) -> None:
    if users_repo.get_by_username(username) is not None:
        return
    password_hash, password_salt = hash_password(DUMMY_PASSWORD)
    users_repo.create_user(
        username=username, role=role, full_name=full_name, email=None,
        auth_type=AUTH_TYPE_PASSWORD, password_hash=password_hash, password_salt=password_salt,
    )
