"""Sesión activa (usuario/rol) del proceso en curso — la app maneja una sesión a la vez."""

from __future__ import annotations

from app.config import ROLES_CAN_ACT_AS_AGENTE, ROLE_AGENTE_PAE
from app.db.repositories.users import User

_current_user: User | None = None


def start(user: User) -> None:
    global _current_user
    _current_user = user


def current() -> User | None:
    return _current_user


def end() -> None:
    global _current_user
    _current_user = None


def can_act_as_agente(user: User | None = None) -> bool:
    user = user or _current_user
    if user is None:
        return False
    return user.role == ROLE_AGENTE_PAE or user.role in ROLES_CAN_ACT_AS_AGENTE
