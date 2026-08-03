from pathlib import Path

import openpyxl

from app.auth.crypto_certs import generate_certificate_bundle, load_bundle
from app.config import AUTH_TYPE_CERTIFICADO, AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.excel_io.mandamientos_export import build_agente_envelope
from app.excel_io.mandamientos_import import parse_agente_export_file, parse_mandamientos_file
from app.excel_io.mcdiep_format import write_envelope


def _write_raw_excel(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["irrelevant title row"])  # fila 1 (se omite)
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE"])  # fila 2 (se omite)
    ws.append(["x1", "F-001", "CP-001", "Juan Pérez"])
    ws.append(["x2", "F-002", "CP-002", "María López"])
    ws.append(["TOTAL", "", "", ""])  # última fila (se omite)
    wb.save(path)


def test_parse_mandamientos_file_skips_rows_and_maps_only_bcd(tmp_path):
    path = tmp_path / "origen.xlsx"
    _write_raw_excel(path)

    result = parse_mandamientos_file(path)

    assert result.row_count == 2
    assert result.rows[0] == {"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}
    assert "domicilio" not in result.rows[0]
    assert result.rows[1]["folio"] == "F-002"


def test_parse_mandamientos_file_folio_numerico_sin_decimales(tmp_path):
    path = tmp_path / "origen_numerico.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["irrelevant title row"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE"])
    ws.append(["x1", 1234, "CP-001", "Juan Pérez"])
    ws.append(["TOTAL", "", "", ""])
    wb.save(path)

    result = parse_mandamientos_file(path)

    assert result.rows[0]["folio"] == "1234"


def test_parse_agente_export_file_reads_clean_headers(db, tmp_path):
    agente = users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="a@a.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )
    pfx_bytes, cert_public_pem, cert_serial = generate_certificate_bundle(
        username=agente.username, full_name=agente.full_name, password="clave-segura"
    )
    users_repo.set_certificate(agente.id, cert_public_pem=cert_public_pem, cert_serial=cert_serial)
    agente = users_repo.get_by_id(agente.id)
    private_key, _certificate = load_bundle(pfx_bytes, "clave-segura")

    abogado = users_repo.create_user(
        username="abogado1", role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )

    path = tmp_path / "exportado.mcdiep"
    envelope = build_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}],
        agente=agente, abogado=abogado, private_key=private_key,
    )
    write_envelope(path, envelope)

    result = parse_agente_export_file(path, abogado=abogado)

    assert result.rows == [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}]
    assert result.agente.username == "agente1"
    assert result.document_uuid
    assert result.file_hash
