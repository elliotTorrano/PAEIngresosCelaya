from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def _make_abogado():
    return users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _import_rows(agente_id, *, source_filename, abogado_nombre=None, abogado_id=None, rows):
    revision_import_id = revisiones_repo.create_revision_import(
        agente_id=agente_id, source_filename=source_filename,
        abogado_nombre=abogado_nombre, abogado_id=abogado_id,
    )
    revisiones_repo.add_revision_rows(
        agente_id=agente_id, revision_import_id=revision_import_id,
        source_filename=source_filename, abogado_nombre=abogado_nombre, abogado_id=abogado_id,
        rows=rows,
    )
    return revision_import_id


def _row(folio):
    return {
        "folio": folio, "cta_predial": None, "contribuyente": None, "domicilio": None,
        "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
        "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
    }


def test_add_and_list_revision_rows(db):
    agente = _make_agente()
    abogado = _make_abogado()
    _import_rows(
        agente.id, source_filename="captura_abogado1.xlsx", abogado_nombre="Abogado Uno",
        abogado_id=abogado.id,
        rows=[{
            "folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1",
            "fecha_citatorio": "01/01/2026", "recibe_citatorio": "EN PUERTA", "recibe_citatorio_nombre": None,
            "fecha_notificacion": "02/01/2026", "quien_recibe": "EN PUERTA", "quien_recibe_nombre": None,
        }],
    )

    rows = revisiones_repo.list_revision_rows(agente.id)
    assert len(rows) == 1
    assert rows[0].folio == "F-001"
    assert rows[0].source_filename == "captura_abogado1.xlsx"
    assert rows[0].abogado_nombre == "Abogado Uno"
    assert rows[0].fecha_citatorio == "01/01/2026"
    assert rows[0].procede is None
    assert rows[0].abogado_id == abogado.id
    assert rows[0].revision_import_id is not None


def test_update_revision_procede(db):
    agente = _make_agente()
    _import_rows(agente.id, source_filename="x.xlsx", rows=[_row("F-001")])
    row_id = revisiones_repo.list_revision_rows(agente.id)[0].id

    revisiones_repo.update_revision_procede(row_id, "PROCEDE")

    refreshed = revisiones_repo.list_revision_rows(agente.id)[0]
    assert refreshed.procede == "PROCEDE"


def test_list_revision_rows_filters_by_agente(db):
    agente1 = _make_agente()
    agente2 = users_repo.create_user(
        username="agente2", role=ROLE_AGENTE_PAE, full_name="Agente Dos", email="a2@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    _import_rows(agente1.id, source_filename="a1.xlsx", rows=[_row("F1")])
    _import_rows(agente2.id, source_filename="a2.xlsx", rows=[_row("F2")])

    rows1 = revisiones_repo.list_revision_rows(agente1.id)
    assert len(rows1) == 1
    assert rows1[0].folio == "F1"


# --- Agrupación por archivo importado (revision_imports) -------------------------------

def test_two_imports_stay_separated_by_revision_import_id(db):
    agente = _make_agente()
    import_id_1 = _import_rows(agente.id, source_filename="lote1.xlsx", rows=[_row("F1"), _row("F2")])
    import_id_2 = _import_rows(agente.id, source_filename="lote2.xlsx", rows=[_row("F3")])

    rows_1 = revisiones_repo.list_revision_rows_for_import(import_id_1)
    rows_2 = revisiones_repo.list_revision_rows_for_import(import_id_2)

    assert [r.folio for r in rows_1] == ["F1", "F2"]
    assert [r.folio for r in rows_2] == ["F3"]
    # El histórico consolidado sigue viendo todo (usado por "Exportar revisión").
    assert len(revisiones_repo.list_revision_rows(agente.id)) == 3


def test_list_revision_imports_reports_reviewed_progress(db):
    agente = _make_agente()
    import_id = _import_rows(agente.id, source_filename="lote1.xlsx", rows=[_row("F1"), _row("F2")])

    imports = revisiones_repo.list_revision_imports(agente.id)
    assert len(imports) == 1
    assert imports[0].id == import_id
    assert imports[0].total_rows == 2
    assert imports[0].reviewed_rows == 0
    assert imports[0].is_reviewed is False

    rows = revisiones_repo.list_revision_rows_for_import(import_id)
    revisiones_repo.update_revision_procede(rows[0].id, "PROCEDE")

    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].reviewed_rows == 1
    assert imports[0].is_reviewed is False  # falta una fila

    revisiones_repo.update_revision_procede(rows[1].id, "NO PROCEDE")

    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].reviewed_rows == 2
    assert imports[0].is_reviewed is True


def test_import_status_transitions_with_procede_changes(db):
    from app.db.repositories.revisiones import (
        STATUS_EN_REVISION,
        STATUS_PENDIENTE_REPORTE,
    )

    agente = _make_agente()
    import_id = _import_rows(agente.id, source_filename="lote1.xlsx", rows=[_row("F1"), _row("F2")])
    rows = revisiones_repo.list_revision_rows_for_import(import_id)

    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].status == STATUS_EN_REVISION

    revisiones_repo.update_revision_procede(rows[0].id, "PROCEDE")
    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].status == STATUS_EN_REVISION  # falta una fila

    revisiones_repo.update_revision_procede(rows[1].id, "NO PROCEDE")
    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].status == STATUS_PENDIENTE_REPORTE

    # Si se destranca una fila (vuelve a quedar sin marcar), regresa a EN_REVISION.
    revisiones_repo.update_revision_procede(rows[1].id, None)
    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].status == STATUS_EN_REVISION


def test_reported_status_does_not_revert_automatically(db):
    from app.db.connection import get_connection
    from app.db.repositories.revisiones import STATUS_REPORTE_ENVIADO

    agente = _make_agente()
    import_id = _import_rows(agente.id, source_filename="lote1.xlsx", rows=[_row("F1")])
    row_id = revisiones_repo.list_revision_rows_for_import(import_id)[0].id
    revisiones_repo.update_revision_procede(row_id, "PROCEDE")

    # Simula que ya se envió como reporte (fase todavía no expuesta en la UI).
    conn = get_connection()
    conn.execute("UPDATE revision_imports SET status = ? WHERE id = ?", (STATUS_REPORTE_ENVIADO, import_id))
    conn.commit()

    # Editar una fila después de "enviado" no debe revertir el estado solo.
    revisiones_repo.update_revision_procede(row_id, None)
    imports = revisiones_repo.list_revision_imports(agente.id)
    assert imports[0].status == STATUS_REPORTE_ENVIADO


def test_list_revision_imports_filters_by_agente(db):
    agente1 = _make_agente()
    agente2 = users_repo.create_user(
        username="agente2", role=ROLE_AGENTE_PAE, full_name="Agente Dos", email="a2@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    _import_rows(agente1.id, source_filename="a1.xlsx", rows=[_row("F1")])
    _import_rows(agente2.id, source_filename="a2.xlsx", rows=[_row("F2")])

    imports1 = revisiones_repo.list_revision_imports(agente1.id)
    assert len(imports1) == 1
    assert imports1[0].source_filename == "a1.xlsx"
