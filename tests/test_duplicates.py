from pathlib import Path

from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.duplicates import find_duplicate_filenames


def test_repeated_filename_within_same_selection_is_flagged():
    paths = [Path("archivo1.xlsx"), Path("archivo2.xlsx"), Path("archivo2.xlsx")]
    duplicates = find_duplicate_filenames(paths)

    assert duplicates == ["archivo2.xlsx"]


def test_filename_already_in_current_batch_is_flagged():
    paths = [Path("archivo1.xlsx"), Path("archivo2.xlsx")]
    duplicates = find_duplicate_filenames(paths, already_in_batch={"archivo1.xlsx"})

    assert duplicates == ["archivo1.xlsx"]


def test_no_duplicates_for_new_files():
    duplicates = find_duplicate_filenames([Path("nuevo.xlsx")])

    assert duplicates == []


def test_historical_reuse_of_same_filename_is_not_a_duplicate(db):
    """El mismo nombre de archivo puede volver a subirse en el futuro (otro mes,
    una corrección) sin que se bloquee -- sólo importa el lote que se está
    preparando en este momento, no el histórico completo."""
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )
    req_repo.record_imported_file(
        original_filename="mensual.xlsx", agente_id=agente.id, abogado_id=abogado.id, row_count=10,
    )

    # Nueva selección, en un lote distinto: el histórico no debe afectarla.
    duplicates = find_duplicate_filenames([Path("mensual.xlsx")])

    assert duplicates == []
