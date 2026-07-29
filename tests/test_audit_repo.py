from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.connection import get_connection
from app.db.repositories import audit as audit_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo


def _make_agente_abogado():
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    return agente, abogado


def test_list_imported_files_resolves_names(db):
    agente, abogado = _make_agente_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.record_imported_file(
        original_filename="lote1.xlsx", agente_id=agente.id, abogado_id=abogado.id,
        batch_id=batch_id, row_count=3,
    )

    rows = audit_repo.list_imported_files(get_connection())

    assert len(rows) == 1
    assert rows[0]["original_filename"] == "lote1.xlsx"
    assert rows[0]["row_count"] == 3
    assert rows[0]["agente_nombre"] == "Agente Uno"
    assert rows[0]["abogado_nombre"] == "Abogado Uno"
    assert rows[0]["imported_at"] is not None


def test_list_batches_counts_captured_rows(db):
    agente, abogado = _make_agente_abogado()
    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.add_rows(
        batch_id,
        [
            {"folio": "F1", "cta_predial": "C1", "contribuyente": "X", "domicilio": "D1"},
            {"folio": "F2", "cta_predial": "C2", "contribuyente": "Y", "domicilio": "D2"},
        ],
    )
    rows = req_repo.list_rows(batch_id)
    req_repo.update_row_capture(
        rows[0].id, fecha_notificacion="01/01/2026", quien_recibe="EN PUERTA", quien_recibe_nombre=None
    )

    batches = audit_repo.list_batches(get_connection())

    assert len(batches) == 1
    assert batches[0]["agente_nombre"] == "Agente Uno"
    assert batches[0]["abogado_nombre"] == "Abogado Uno"
    assert batches[0]["total_filas"] == 2
    assert batches[0]["filas_capturadas"] == 1
