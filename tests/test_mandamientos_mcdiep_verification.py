import pytest

from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.mandamientos_export import build_agente_envelope, export_captured
from app.excel_io.mandamientos_import import McdiepVerificationError, parse_agente_export_file


def _make_agente_with_cert(username="agente1"):
    agente = users_repo.create_user(
        username=username, role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-segura"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    private_key, _certificate = load_bundle(pfx_bytes, "clave-segura")
    return users_repo.get_by_id(agente.id), private_key


def _make_abogado(username="abogado1"):
    return users_repo.create_user(
        username=username, role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _export(path, *, agente, abogado, private_key, rows=None):
    envelope = build_agente_envelope(
        rows or [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}],
        agente=agente, abogado=abogado, private_key=private_key,
    )
    mcdiep_format.write_envelope(path, envelope)


def test_valid_file_returns_rows_and_signer(tmp_path, db):
    agente, private_key = _make_agente_with_cert()
    abogado = _make_abogado()
    path = tmp_path / "lista.mcdiep"
    _export(path, agente=agente, abogado=abogado, private_key=private_key)

    result = parse_agente_export_file(path, abogado=abogado)

    assert len(result.rows) == 1
    assert result.agente.id == agente.id


def test_unknown_signer_is_rejected(tmp_path, db):
    abogado = _make_abogado()
    path = tmp_path / "fantasma.mcdiep"
    mcdiep_format.write_envelope(
        path,
        mcdiep_format.McdiepEnvelope(
            kind=mcdiep_format.KIND_AGENTE_TO_ABOGADO,
            signer_username="no_existe",
            target_username=abogado.username,
            payload={"headers": [], "rows": []},
            signature=b"cualquier-cosa",
        ),
    )

    with pytest.raises(McdiepVerificationError, match="no existe"):
        parse_agente_export_file(path, abogado=abogado)


def test_wrong_target_abogado_is_rejected(tmp_path, db):
    agente, private_key = _make_agente_with_cert()
    intended_abogado = _make_abogado("abogado1")
    other_abogado = _make_abogado("abogado2")
    path = tmp_path / "lista.mcdiep"
    _export(path, agente=agente, abogado=intended_abogado, private_key=private_key)

    with pytest.raises(McdiepVerificationError, match="abogado1"):
        parse_agente_export_file(path, abogado=other_abogado)


def test_wrong_kind_is_rejected(tmp_path, db):
    """Una captura del Abogado (abogado_to_agente) no debe abrirse como si
    fuera una lista del Agente (agente_to_abogado)."""
    abogado = _make_abogado()
    path = tmp_path / "captura.mcdiep"
    export_captured([], path)

    with pytest.raises(McdiepVerificationError):
        parse_agente_export_file(path, abogado=abogado)
