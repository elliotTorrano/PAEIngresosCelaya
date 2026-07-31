import pytest

from app.excel_io import mcdiep_format


def test_write_read_roundtrip_unsigned(tmp_path):
    envelope = mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_ABOGADO_TO_AGENTE,
        signer_username=None,
        target_username=None,
        payload={"headers": ["FOLIO"], "rows": [{"folio": "F-001"}]},
        signature=None,
    )
    path = tmp_path / "archivo.mcdiep"
    mcdiep_format.write_envelope(path, envelope)
    read_back = mcdiep_format.read_envelope(path)

    assert read_back.kind == mcdiep_format.KIND_ABOGADO_TO_AGENTE
    assert read_back.signer_username is None
    assert read_back.target_username is None
    assert read_back.payload == {"headers": ["FOLIO"], "rows": [{"folio": "F-001"}]}
    assert read_back.signature is None


def test_write_read_roundtrip_signed(tmp_path):
    payload = {"headers": ["FOLIO"], "rows": [{"folio": "F-001"}]}
    envelope = mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_AGENTE_TO_ABOGADO,
        signer_username="agente1",
        target_username="abogado1",
        payload=payload,
        signature=b"\x01\x02\x03fake-signature",
    )
    path = tmp_path / "archivo.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    read_back = mcdiep_format.read_envelope(path)

    assert read_back.kind == mcdiep_format.KIND_AGENTE_TO_ABOGADO
    assert read_back.signer_username == "agente1"
    assert read_back.target_username == "abogado1"
    assert read_back.payload == payload
    assert read_back.signature == b"\x01\x02\x03fake-signature"


def test_read_rejects_file_without_magic(tmp_path):
    path = tmp_path / "no_es_mcdiep.mcdiep"
    path.write_bytes(b"esto no es un archivo mcdiep, es texto plano")

    with pytest.raises(mcdiep_format.InvalidMcdiepFile):
        mcdiep_format.read_envelope(path)


def test_read_rejects_plain_xlsx_masquerading_as_mcdiep(tmp_path):
    import openpyxl

    path = tmp_path / "excel_disfrazado.mcdiep"
    wb = openpyxl.Workbook()
    wb.save(path)

    with pytest.raises(mcdiep_format.InvalidMcdiepFile):
        mcdiep_format.read_envelope(path)


def test_read_rejects_truncated_file(tmp_path):
    envelope = mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_ABOGADO_TO_AGENTE, signer_username=None, target_username=None,
        payload={"rows": []}, signature=None,
    )
    path = tmp_path / "truncado.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    full_bytes = path.read_bytes()
    path.write_bytes(full_bytes[: len(full_bytes) - 5])  # corta el final

    with pytest.raises(mcdiep_format.InvalidMcdiepFile):
        mcdiep_format.read_envelope(path)


def test_read_rejects_file_with_corrupted_middle_bytes(tmp_path):
    """Editar el archivo a mano (p. ej. con un editor de texto) rompe el
    framing binario o el JSON comprimido -- exactamente lo que se busca."""
    envelope = mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_AGENTE_TO_ABOGADO, signer_username="agente1", target_username="abogado1",
        payload={"rows": [{"folio": "F-001"}]}, signature=b"firma-falsa",
    )
    path = tmp_path / "editado.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    corrupted = bytearray(path.read_bytes())
    corrupted[-10] ^= 0xFF
    path.write_bytes(bytes(corrupted))

    with pytest.raises(mcdiep_format.InvalidMcdiepFile):
        mcdiep_format.read_envelope(path)


def test_signable_bytes_is_deterministic():
    payload = {"b": 2, "a": 1}
    first = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, "abogado1", payload)
    second = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, "abogado1", payload)
    assert first == second


def test_signable_bytes_changes_with_target():
    payload = {"rows": []}
    for_a = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, "abogado1", payload)
    for_b = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, "abogado2", payload)
    assert for_a != for_b


def test_signable_bytes_changes_with_payload():
    same_target = "abogado1"
    a = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, same_target, {"rows": [1]})
    b = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, same_target, {"rows": [2]})
    assert a != b
