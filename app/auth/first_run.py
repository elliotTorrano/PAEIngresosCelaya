"""Asistente de primer arranque: crea el súper-usuario único y el primer Administrador."""

from __future__ import annotations

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_ADMINISTRADOR, ROLE_SUPERUSUARIO
from app.db.repositories import users as users_repo


def needs_first_run() -> bool:
    return users_repo.count_by_role(ROLE_SUPERUSUARIO) == 0


def create_superuser(*, username: str, full_name: str, email: str) -> users_repo.User:
    return users_repo.create_user(
        username=username,
        role=ROLE_SUPERUSUARIO,
        full_name=full_name,
        email=email,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def create_first_administrator(*, username: str, full_name: str, email: str) -> users_repo.User:
    if users_repo.count_by_role(ROLE_ADMINISTRADOR) > 0:
        raise ValueError("Ya existe un Administrador; sólo puede haber uno.")
    return users_repo.create_user(
        username=username,
        role=ROLE_ADMINISTRADOR,
        full_name=full_name,
        email=email,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
