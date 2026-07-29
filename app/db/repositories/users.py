"""Repositorio de usuarios: alta, consulta y actualización de credenciales."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection


@dataclass
class User:
    id: int
    username: str
    role: str
    full_name: str
    email: str | None
    auth_type: str
    password_hash: str | None
    password_salt: str | None
    cert_public_pem: str | None
    cert_serial: str | None
    must_change_password: bool
    active: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            full_name=row["full_name"],
            email=row["email"],
            auth_type=row["auth_type"],
            password_hash=row["password_hash"],
            password_salt=row["password_salt"],
            cert_public_pem=row["cert_public_pem"],
            cert_serial=row["cert_serial"],
            must_change_password=bool(row["must_change_password"]),
            active=bool(row["active"]),
        )


def count_by_role(role: str) -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role = ?", (role,)).fetchone()
    return row["n"]


def get_by_username(username: str) -> User | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return User.from_row(row) if row else None


def get_by_id(user_id: int) -> User | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row) if row else None


def list_by_role(role: str, active_only: bool = True) -> list[User]:
    conn = get_connection()
    query = "SELECT * FROM users WHERE role = ?"
    params: list = [role]
    if active_only:
        query += " AND active = 1"
    query += " ORDER BY full_name"
    rows = conn.execute(query, params).fetchall()
    return [User.from_row(r) for r in rows]


def create_user(
    *,
    username: str,
    role: str,
    full_name: str,
    email: str | None,
    auth_type: str,
    password_hash: str | None = None,
    password_salt: str | None = None,
    must_change_password: bool = False,
) -> User:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO users (username, role, full_name, email, auth_type, password_hash, password_salt, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (username, role, full_name, email, auth_type, password_hash, password_salt, 1 if must_change_password else 0),
    )
    conn.commit()
    return get_by_id(cur.lastrowid)  # type: ignore[return-value]


def set_certificate(user_id: int, *, cert_public_pem: str, cert_serial: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE users
        SET cert_public_pem = ?, cert_serial = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (cert_public_pem, cert_serial, user_id),
    )
    conn.commit()


def set_password(user_id: int, *, password_hash: str, password_salt: str, must_change_password: bool = False) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE users
        SET password_hash = ?, password_salt = ?, must_change_password = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (password_hash, password_salt, 1 if must_change_password else 0, user_id),
    )
    conn.commit()


def update_identity(user_id: int, *, username: str, full_name: str, email: str | None) -> None:
    """Cambia usuario/nombre/correo. El llamador es responsable de validar unicidad
    de `username` y de exigir la confirmación por certificado correspondiente."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE users
        SET username = ?, full_name = ?, email = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (username, full_name, email, user_id),
    )
    conn.commit()


def set_active(user_id: int, active: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE users SET active = ?, updated_at = datetime('now') WHERE id = ?",
        (1 if active else 0, user_id),
    )
    conn.commit()


def has_certificate(user: User) -> bool:
    return bool(user.cert_public_pem and user.cert_serial)


def clear_certificate(user_id: int) -> None:
    """Borra el certificado registrado, habilitando un nuevo enrolamiento en el siguiente login."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE users
        SET cert_public_pem = NULL, cert_serial = NULL, updated_at = datetime('now')
        WHERE id = ?
        """,
        (user_id,),
    )
    conn.commit()


def get_administrator() -> User | None:
    from app.config import ROLE_ADMINISTRADOR

    users = list_by_role(ROLE_ADMINISTRADOR, active_only=False)
    return users[0] if users else None
