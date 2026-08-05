from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import mandamientos as mand_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo


def _make_agente(username="agente1", full_name="Agente Uno"):
    return users_repo.create_user(
        username=username, role=ROLE_AGENTE_PAE, full_name=full_name, email=f"{username}@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado(username="abogado1", full_name="Abogado Uno"):
    return users_repo.create_user(
        username=username, role=ROLE_ABOGADO, full_name=full_name, email=f"{username}@a.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


# --- set_batch_export_path graba el timestamp de exportación ---------------------

def test_set_batch_export_path_stamps_agente_exported_at(db):
    agente = _make_agente()
    abogado = _make_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)

    req_repo.set_batch_export_path(batch_id, agente_path="/x/req.mcdiep")

    batch = req_repo.get_batch(batch_id)
    assert batch["exported_agente_path"] == "/x/req.mcdiep"
    assert batch["agente_exported_at"] is not None
    assert batch["abogado_exported_at"] is None


def test_set_batch_export_path_stamps_abogado_exported_at(db):
    agente = _make_agente()
    abogado = _make_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)

    req_repo.set_batch_export_path(batch_id, abogado_path="/x/req_entrega.mcdiep")

    batch = req_repo.get_batch(batch_id)
    assert batch["exported_abogado_path"] == "/x/req_entrega.mcdiep"
    assert batch["abogado_exported_at"] is not None
    assert batch["agente_exported_at"] is None


def test_set_batch_export_path_uuid_only_does_not_stamp_agente_exported_at(db):
    """El import del Abogado sólo manda agente_uuid/agente_hash (nunca
    agente_path) al leer el .mcdiep recibido -- no debe registrarse como si
    el Agente hubiera exportado desde ESTA máquina."""
    agente = _make_agente()
    abogado = _make_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)

    req_repo.set_batch_export_path(batch_id, agente_uuid="uuid-1", agente_hash="hash-1")

    batch = req_repo.get_batch(batch_id)
    assert batch["agente_export_uuid"] == "uuid-1"
    assert batch["agente_exported_at"] is None
    assert batch["exported_agente_path"] is None


# --- list_exported_batches_for_agente/abogado -------------------------------------

def test_list_exported_batches_for_agente_only_includes_exported(db):
    agente = _make_agente()
    abogado = _make_abogado()
    exported_batch = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(exported_batch, [{"folio": "1", "cta_predial": None, "contribuyente": None, "domicilio": None}])
    req_repo.set_batch_export_path(exported_batch, agente_path="/x/exportado.mcdiep")
    req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)  # nunca exportado

    rows = req_repo.list_exported_batches_for_agente(agente.id)

    assert len(rows) == 1
    assert rows[0]["exported_agente_path"] == "/x/exportado.mcdiep"
    assert rows[0]["abogado_nombre"] == "Abogado Uno"
    assert rows[0]["row_count"] == 1
    assert rows[0]["agente_exported_at"] is not None


def test_list_exported_batches_for_abogado_only_includes_exported(db):
    agente = _make_agente()
    abogado = _make_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.set_batch_export_path(batch_id, abogado_path="/x/entrega.mcdiep")

    rows = req_repo.list_exported_batches_for_abogado(abogado.id)

    assert len(rows) == 1
    assert rows[0]["exported_abogado_path"] == "/x/entrega.mcdiep"
    assert rows[0]["agente_nombre"] == "Agente Uno"


def test_list_exported_batches_mandamiento_mirrors_requerimiento(db):
    agente = _make_agente()
    abogado = _make_abogado()
    batch_id = mand_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    mand_repo.set_batch_export_path(batch_id, agente_path="/x/mand.mcdiep")

    rows = mand_repo.list_exported_batches_for_agente(agente.id)

    assert len(rows) == 1
    assert rows[0]["exported_agente_path"] == "/x/mand.mcdiep"
