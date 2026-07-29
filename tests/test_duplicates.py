from pathlib import Path

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.duplicates import find_duplicate_filenames


def test_find_duplicate_filenames(db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    batch_id = req_repo.create_batch(abogado_id=abogado.id, agente_id=agente.id)
    req_repo.record_imported_file(
        original_filename="archivo1.xlsx", agente_id=agente.id, abogado_id=abogado.id,
        batch_id=batch_id, row_count=10,
    )

    paths = [Path("archivo1.xlsx"), Path("archivo2.xlsx"), Path("archivo2.xlsx")]
    duplicates = find_duplicate_filenames(agente.id, paths)

    assert duplicates == ["archivo1.xlsx", "archivo2.xlsx"]


def test_no_duplicates_for_new_files(db):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )

    duplicates = find_duplicate_filenames(agente.id, [Path("nuevo.xlsx")])

    assert duplicates == []
