"""Directorio remoto mínimo de usuarios (Agente/Abogado/Reporteador) en Turso.

Solo existe para que una cuenta dada de alta por el Administrador en una
máquina aparezca en las demás sin reinstalar -- nunca sincroniza expedientes
ni ningún otro dato del programa. Se habla con Turso por su API HTTP
pública (POST .../v2/pipeline, ver docs.turso.tech/sdk/http/reference) vía
`urllib.request` de la librería estándar -- el mismo mecanismo que ya usa
`app/update/checker.py::check_for_update()` contra la API de GitHub. No se
usa el paquete `libsql`: no publica rueda para cp314-win_amd64 en PyPI (solo
código fuente en Rust, que requeriría instalar un compilador de Rust y
herramientas de MSVC sólo para esta función), y la API HTTP hace exactamente
lo mismo sin depender de ningún paquete nuevo.

Toda llamada de red queda completamente blindada (try/except silencioso,
nunca propaga): si falla por lo que sea (sin internet, token vencido, tabla
no existe todavía), el programa sigue funcionando exactamente igual que
hoy, solo que sin la novedad hasta el siguiente intento con conexión.

`cert_public_pem`/`cert_serial` viajan hacia Turso (para que se pueda saber,
sin ir máquina por máquina, si alguien ya enroló su certificado), pero
NUNCA se leen de vuelta hacia ninguna `pae.db` local -- ver `_apply_row`.
Copiarlos marcaría una cuenta local como "ya tiene certificado" sin que
exista ahí la llave privada correspondiente (que vive solo en la máquina
donde se enroló), dejando a esa persona sin poder iniciar sesión.
"""

from __future__ import annotations

import json
import urllib.request

from app.config import DUMMY_USERNAMES, ROLE_ABOGADO, ROLE_AGENTE_PAE, ROLE_REPORTEADOR
from app.db.repositories import settings
from app.db.repositories import users as users_repo
from app.sync import config as sync_config

SYNCED_ROLES = (ROLE_AGENTE_PAE, ROLE_ABOGADO, ROLE_REPORTEADOR)

REQUEST_TIMEOUT_SECONDS = 5

_ENSURE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS directory_users (
    username             TEXT PRIMARY KEY,
    role                 TEXT NOT NULL,
    full_name            TEXT NOT NULL,
    email                TEXT,
    auth_type            TEXT NOT NULL,
    password_hash        TEXT,
    password_salt        TEXT,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    active               INTEGER NOT NULL DEFAULT 1,
    cert_public_pem       TEXT,
    cert_serial           TEXT,
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_UPSERT_SQL = """
INSERT OR REPLACE INTO directory_users (
    username, role, full_name, email, auth_type,
    password_hash, password_salt, must_change_password, active,
    cert_public_pem, cert_serial, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
"""

_PULL_COLUMNS = (
    "username", "role", "full_name", "email", "auth_type",
    "password_hash", "password_salt", "must_change_password", "active",
)


def _http_base(database_url: str) -> str:
    """Turso suele dar la URL como libsql://...; la API HTTP usa https://."""
    if database_url.startswith("libsql://"):
        return "https://" + database_url[len("libsql://"):]
    return database_url


def _arg(value) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    return {"type": "text", "value": str(value)}


def _cell_value(cell: dict):
    cell_type = cell.get("type")
    if cell_type == "null":
        return None
    if cell_type == "integer":
        return int(cell["value"])
    if cell_type == "float":
        return float(cell["value"])
    return cell.get("value")


def _pipeline(database_url: str, token: str, statements: list[tuple[str, list | None]]) -> list[dict]:
    """Ejecuta una o más sentencias SQL en una sola llamada HTTP. Devuelve la
    lista de resultados (`result`, con `cols`/`rows`) en el mismo orden."""
    requests_payload = [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in (args or [])]}}
        for sql, args in statements
    ]
    requests_payload.append({"type": "close"})
    body = json.dumps({"requests": requests_payload}).encode("utf-8")

    request = urllib.request.Request(
        f"{_http_base(database_url)}/v2/pipeline",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)

    results = []
    for item in payload["results"]:
        if item.get("type") != "ok":
            raise RuntimeError(str(item.get("error")))
        response = item["response"]
        if response.get("type") != "execute":
            continue  # p. ej. la respuesta al "close" final, que no trae "result"
        results.append(response["result"])
    return results


def push_user(user: users_repo.User) -> None:
    """Sube (upsert) la cuenta a Turso. Best-effort: nunca lanza."""
    if user.username in DUMMY_USERNAMES or user.role not in SYNCED_ROLES:
        return
    try:
        token = settings.get(settings.KEY_TURSO_WRITE_TOKEN)
        database_url = sync_config.database_url()
        if not token or not database_url:
            return
        _pipeline(database_url, token, [
            (_ENSURE_TABLE_SQL, None),
            (_UPSERT_SQL, [
                user.username, user.role, user.full_name, user.email, user.auth_type,
                user.password_hash, user.password_salt,
                1 if user.must_change_password else 0, 1 if user.active else 0,
                user.cert_public_pem, user.cert_serial,
            ]),
        ])
    except Exception:
        pass


def pull_and_apply() -> None:
    """Baja el directorio remoto y crea/actualiza cuentas locales. Best-effort.

    A propósito NO manda `_ENSURE_TABLE_SQL` aquí: un token de solo lectura
    (el que llevan todas las instalaciones) rechaza el pipeline COMPLETO si
    cualquiera de sus sentencias es de escritura -- aunque sea un `CREATE
    TABLE IF NOT EXISTS` inofensivo -- así que incluirlo tumbaría también el
    SELECT. Sólo `push_user` (con el token de escritura) crea la tabla; si
    todavía no existe (nadie ha dado de alta a nadie desde esta función),
    el SELECT falla con un error de "no existe la tabla", que este mismo
    try/except ya trata como "no hay nada que traer todavía"."""
    try:
        token = sync_config.read_only_token()
        database_url = sync_config.database_url()
        if not token or not database_url:
            return
        results = _pipeline(database_url, token, [
            (f"SELECT {', '.join(_PULL_COLUMNS)} FROM directory_users", None),
        ])
        select_result = results[-1]
        col_names = [c["name"] for c in select_result["cols"]]
        rows = [
            dict(zip(col_names, (_cell_value(cell) for cell in raw_row)))
            for raw_row in select_result["rows"]
        ]
    except Exception:
        return

    for row in rows:
        try:
            _apply_row(row)
        except Exception:
            continue


def _apply_row(row: dict) -> None:
    username = row["username"]
    if username in DUMMY_USERNAMES or row["role"] not in SYNCED_ROLES:
        return

    existing = users_repo.get_by_username(username)
    if existing is None:
        users_repo.create_user(
            username=username,
            role=row["role"],
            full_name=row["full_name"],
            email=row["email"],
            auth_type=row["auth_type"],
            password_hash=row["password_hash"],
            password_salt=row["password_salt"],
            must_change_password=bool(row["must_change_password"]),
        )
        return

    if existing.full_name != row["full_name"] or existing.email != row["email"]:
        users_repo.update_identity(
            existing.id, username=existing.username,
            full_name=row["full_name"], email=row["email"],
        )
    if existing.active != bool(row["active"]):
        users_repo.set_active(existing.id, bool(row["active"]))
