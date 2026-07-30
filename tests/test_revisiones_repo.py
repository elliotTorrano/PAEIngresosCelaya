from app.config import AUTH_TYPE_CERTIFICADO, ROLE_AGENTE_PAE
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import users as users_repo


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_add_and_list_revision_rows(db):
    agente = _make_agente()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id,
        source_filename="captura_abogado1.xlsx",
        abogado_nombre="Abogado Uno",
        rows=[
            {
                "folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1",
                "fecha_citatorio": "01/01/2026", "recibe_citatorio": "EN PUERTA", "recibe_citatorio_nombre": None,
                "fecha_notificacion": "02/01/2026", "quien_recibe": "EN PUERTA", "quien_recibe_nombre": None,
            }
        ],
    )

    rows = revisiones_repo.list_revision_rows(agente.id)
    assert len(rows) == 1
    assert rows[0].folio == "F-001"
    assert rows[0].source_filename == "captura_abogado1.xlsx"
    assert rows[0].abogado_nombre == "Abogado Uno"
    assert rows[0].fecha_citatorio == "01/01/2026"
    assert rows[0].procede is None


def test_update_revision_procede(db):
    agente = _make_agente()
    revisiones_repo.add_revision_rows(
        agente_id=agente.id, source_filename="x.xlsx", abogado_nombre=None,
        rows=[{
            "folio": "F-001", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )
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
    revisiones_repo.add_revision_rows(
        agente_id=agente1.id, source_filename="a1.xlsx", abogado_nombre=None,
        rows=[{
            "folio": "F1", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )
    revisiones_repo.add_revision_rows(
        agente_id=agente2.id, source_filename="a2.xlsx", abogado_nombre=None,
        rows=[{
            "folio": "F2", "cta_predial": None, "contribuyente": None, "domicilio": None,
            "fecha_citatorio": None, "recibe_citatorio": None, "recibe_citatorio_nombre": None,
            "fecha_notificacion": None, "quien_recibe": None, "quien_recibe_nombre": None,
        }],
    )

    rows1 = revisiones_repo.list_revision_rows(agente1.id)
    assert len(rows1) == 1
    assert rows1[0].folio == "F1"
