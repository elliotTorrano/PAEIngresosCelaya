import json
from unittest.mock import patch

import pytest

from app.config import (
    AUTH_TYPE_CERTIFICADO,
    AUTH_TYPE_PASSWORD,
    DUMMY_AGENTE_USERNAME,
    ROLE_ABOGADO,
    ROLE_ADMINISTRADOR,
    ROLE_AGENTE_PAE,
)
from app.db.repositories import settings as settings_repo
from app.db.repositories import users as users_repo
from app.sync import user_directory


def _fake_response(payload_dict):
    body = json.dumps(payload_dict).encode("utf-8")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body

    return _Resp()


def _ok_result(cols=None, rows=None):
    return {
        "type": "ok",
        "response": {"type": "execute", "result": {"cols": cols or [], "rows": rows or []}},
    }


def _configure_sync(monkeypatch, *, write_token="write-tok", read_token="read-tok"):
    monkeypatch.setattr(user_directory.sync_config, "database_url", lambda: "https://example.turso.io")
    monkeypatch.setattr(user_directory.sync_config, "read_only_token", lambda: read_token)
    if write_token is not None:
        settings_repo.set(settings_repo.KEY_TURSO_WRITE_TOKEN, write_token)


# --- push_user ------------------------------------------------------------------

def test_push_user_skips_dummy_username(db, monkeypatch):
    _configure_sync(monkeypatch)
    user = users_repo.create_user(
        username=DUMMY_AGENTE_USERNAME, role=ROLE_AGENTE_PAE, full_name="X", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    with patch("app.sync.user_directory.urllib.request.urlopen") as mock_urlopen:
        user_directory.push_user(user)
    mock_urlopen.assert_not_called()


def test_push_user_skips_role_not_synced(db, monkeypatch):
    _configure_sync(monkeypatch)
    user = users_repo.create_user(
        username="admin1", role=ROLE_ADMINISTRADOR, full_name="X", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    with patch("app.sync.user_directory.urllib.request.urlopen") as mock_urlopen:
        user_directory.push_user(user)
    mock_urlopen.assert_not_called()


def test_push_user_skips_when_no_write_token_configured(db, monkeypatch):
    _configure_sync(monkeypatch, write_token=None)
    user = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="X", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    with patch("app.sync.user_directory.urllib.request.urlopen") as mock_urlopen:
        user_directory.push_user(user)
    mock_urlopen.assert_not_called()


def test_push_user_sends_upsert_with_cert_fields(db, monkeypatch):
    _configure_sync(monkeypatch)
    user = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@x.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    users_repo.set_certificate(user.id, cert_public_pem="PEM", cert_serial="SERIAL")
    user = users_repo.get_by_id(user.id)

    response = _fake_response({"results": [_ok_result(), _ok_result()]})
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=response) as mock_urlopen:
        user_directory.push_user(user)

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.headers["Authorization"] == "Bearer write-tok"
    body = json.loads(request.data)
    upsert_stmt = body["requests"][1]["stmt"]
    assert "INSERT OR REPLACE" in upsert_stmt["sql"]
    values = [arg.get("value") for arg in upsert_stmt["args"]]
    assert values[0] == "agente1"
    assert "PEM" in values
    assert "SERIAL" in values


def test_push_user_never_raises_on_network_error(db, monkeypatch):
    _configure_sync(monkeypatch)
    user = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="X", email=None,
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    with patch("app.sync.user_directory.urllib.request.urlopen", side_effect=OSError("sin conexión")):
        user_directory.push_user(user)  # no debe lanzar


# --- pull_and_apply ---------------------------------------------------------------

def _select_result(rows):
    cols = [{"name": c} for c in user_directory._PULL_COLUMNS]
    typed_rows = []
    for row in rows:
        typed_row = []
        for value in row:
            if value is None:
                typed_row.append({"type": "null"})
            elif isinstance(value, int):
                typed_row.append({"type": "integer", "value": str(value)})
            else:
                typed_row.append({"type": "text", "value": value})
        typed_rows.append(typed_row)
    return _ok_result(cols=cols, rows=typed_rows)


def test_pull_and_apply_creates_new_local_user_without_cert(db, monkeypatch):
    _configure_sync(monkeypatch)
    row = ("agente_nuevo", ROLE_AGENTE_PAE, "Agente Nuevo", "a@x.com", AUTH_TYPE_CERTIFICADO,
           None, None, 0, 1)
    payload = {"results": [_select_result([row])]}
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=_fake_response(payload)):
        user_directory.pull_and_apply()

    created = users_repo.get_by_username("agente_nuevo")
    assert created is not None
    assert created.full_name == "Agente Nuevo"
    assert created.cert_public_pem is None
    assert created.cert_serial is None


def test_pull_and_apply_creates_abogado_with_latest_password(db, monkeypatch):
    _configure_sync(monkeypatch)
    row = ("abogado_nuevo", ROLE_ABOGADO, "Abogado Nuevo", None, AUTH_TYPE_PASSWORD,
           "HASH_VIGENTE", "SALT_VIGENTE", 0, 1)
    payload = {"results": [_select_result([row])]}
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=_fake_response(payload)):
        user_directory.pull_and_apply()

    created = users_repo.get_by_username("abogado_nuevo")
    assert created is not None
    assert created.password_hash == "HASH_VIGENTE"
    assert created.password_salt == "SALT_VIGENTE"
    assert created.must_change_password is False


def test_pull_and_apply_never_overwrites_existing_local_credentials(db, monkeypatch):
    _configure_sync(monkeypatch)
    local = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Nombre Viejo", email="viejo@x.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="LOCAL_HASH", password_salt="LOCAL_SALT",
        must_change_password=False,
    )

    row = ("abogado1", ROLE_ABOGADO, "Nombre Nuevo", "nuevo@x.com", AUTH_TYPE_PASSWORD,
           "REMOTE_HASH", "REMOTE_SALT", 1, 1)
    payload = {"results": [_select_result([row])]}
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=_fake_response(payload)):
        user_directory.pull_and_apply()

    updated = users_repo.get_by_username("abogado1")
    assert updated.id == local.id
    assert updated.full_name == "Nombre Nuevo"
    assert updated.email == "nuevo@x.com"
    assert updated.password_hash == "LOCAL_HASH"
    assert updated.password_salt == "LOCAL_SALT"


def test_pull_and_apply_skips_dummy_and_unsynced_role_rows(db, monkeypatch):
    _configure_sync(monkeypatch)
    rows = [
        (DUMMY_AGENTE_USERNAME, ROLE_AGENTE_PAE, "Dummy", None, AUTH_TYPE_CERTIFICADO, None, None, 0, 1),
        ("admin_remoto", ROLE_ADMINISTRADOR, "Admin", None, AUTH_TYPE_CERTIFICADO, None, None, 0, 1),
    ]
    payload = {"results": [_select_result(rows)]}
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=_fake_response(payload)):
        user_directory.pull_and_apply()

    assert users_repo.get_by_username(DUMMY_AGENTE_USERNAME) is None
    assert users_repo.get_by_username("admin_remoto") is None


def test_pull_and_apply_sends_only_the_select_no_write_statements(db, monkeypatch):
    """Un token de solo lectura de Turso rechaza el pipeline COMPLETO si
    trae cualquier sentencia de escritura -- ver docstring de
    pull_and_apply(). Esta prueba evita que alguien reintroduzca por error
    un CREATE TABLE (u otra escritura) en el pipeline de lectura."""
    _configure_sync(monkeypatch)
    payload = {"results": [_select_result([])]}
    with patch("app.sync.user_directory.urllib.request.urlopen", return_value=_fake_response(payload)) as mock_urlopen:
        user_directory.pull_and_apply()

    request = mock_urlopen.call_args[0][0]
    body = json.loads(request.data)
    statements = [r for r in body["requests"] if r["type"] == "execute"]
    assert len(statements) == 1
    assert statements[0]["stmt"]["sql"].strip().upper().startswith("SELECT")


def test_pull_and_apply_never_raises_on_network_error(db, monkeypatch):
    _configure_sync(monkeypatch)
    with patch("app.sync.user_directory.urllib.request.urlopen", side_effect=OSError("sin conexión")):
        user_directory.pull_and_apply()  # no debe lanzar


def test_pull_and_apply_does_nothing_without_read_token(db, monkeypatch):
    _configure_sync(monkeypatch, read_token=None)
    with patch("app.sync.user_directory.urllib.request.urlopen") as mock_urlopen:
        user_directory.pull_and_apply()
    mock_urlopen.assert_not_called()


# --- otros puntos de llamada: cambio de contraseña ---------------------------------

def test_change_password_dialog_pushes_updated_user(qapp, db):
    from app.auth.passwords import hash_password
    from app.ui.login.change_password_dialog import ChangePasswordDialog

    pwd_hash, salt = hash_password("clave-vieja")
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash=pwd_hash, password_salt=salt,
        must_change_password=True,
    )

    dialog = ChangePasswordDialog(abogado)
    dialog.new_password_input.setText("clave-nueva-6")
    dialog.confirm_password_input.setText("clave-nueva-6")

    with patch("app.ui.login.change_password_dialog.user_directory.push_user") as mock_push:
        dialog._on_save()

    mock_push.assert_called_once()
    assert mock_push.call_args[0][0].username == "abogado1"
    assert mock_push.call_args[0][0].must_change_password is False


def test_apply_update_package_pushes_updated_user(db):
    from app.auth import recovery

    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="old", password_salt="old",
    )
    payload = recovery.build_update_package_set_password(
        username="abogado1", role=ROLE_ABOGADO, password_hash="new_hash", password_salt="new_salt",
        admin_username="admin1",
    )

    with patch("app.auth.recovery.user_directory.push_user") as mock_push:
        recovery.apply_update_package(payload)

    mock_push.assert_called_once()
    pushed_user = mock_push.call_args[0][0]
    assert pushed_user.username == "abogado1"
    assert pushed_user.password_hash == "new_hash"
