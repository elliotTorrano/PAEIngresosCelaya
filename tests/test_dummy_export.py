from unittest.mock import patch

import openpyxl
from PySide6.QtWidgets import QMessageBox
from pypdf import PdfReader

from app.config import AUTH_TYPE_PASSWORD, ROLE_ABOGADO, ROLE_AGENTE_PAE
from app.db.repositories import mandamientos as mand_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import users as users_repo
from app.excel_io.mandamientos_export import build_agente_envelope as build_mandamiento_envelope
from app.excel_io.requerimientos_export import build_agente_envelope
from app.pdf_io import mandamientos_pdf
from app.pdf_io import requerimientos_pdf
from app.ui.agente.mandamientos_generar_view import MandamientosGenerarView
from app.ui.agente.requerimientos_generar_view import RequerimientosGenerarView


def _write_valid_requerimientos_file(path, rows=1):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "E", "DOMICILIO"])
    for i in range(rows):
        ws.append(["x", f"F-{i:03d}", f"CP-{i:03d}", f"Contribuyente {i}", "y", f"Calle {i}"])
    ws.append(["TOTAL", "", "", "", "", ""])
    wb.save(path)


def _write_valid_mandamientos_file(path, rows=1):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(["A", "FOLIO", "CTA PREDIAL", "CONTRIBUYENTE"])
    for i in range(rows):
        ws.append(["x", f"F-{i:03d}", f"CP-{i:03d}", f"Contribuyente {i}"])
    ws.append(["TOTAL", "", "", ""])
    wb.save(path)


def _make_agente_dummy():
    return users_repo.create_user(
        username="agente_dummy", role=ROLE_AGENTE_PAE, full_name="Agente del PAE (prueba)", email=None,
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_abogado(username="abogado1"):
    return users_repo.create_user(
        username=username, role=ROLE_ABOGADO, full_name="Abogado Uno", email="b@b.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


# --- pdf_io: identidad y nombre de archivo de prueba -----------------------------------

def test_dummy_identity_has_no_real_uuid_hash_or_signature():
    identity = requerimientos_pdf.dummy_identity()
    assert identity.uuid == requerimientos_pdf.DUMMY_LABEL
    assert identity.file_hash == requerimientos_pdf.DUMMY_LABEL
    assert identity.signature_b64 is None


def test_suggested_dummy_filename_contains_prueba_and_extension():
    name = requerimientos_pdf.suggested_dummy_filename(
        agente_nombre="Agente del PAE (prueba)", abogado_nombre="Abogado Uno", extension=".mcdiep",
    )
    assert name.endswith(".mcdiep")
    assert "PRUEBA" in name


# --- pdf_io: render con dummy=True (una página, sin QR, con marca de agua) -------------

def test_export_agente_pdf_dummy_renders_single_page(db, tmp_path):
    agente = _make_agente_dummy()
    abogado = _make_abogado()
    rows = [
        {"folio": f"F-{i:03d}", "cta_predial": f"CP-{i:03d}", "contribuyente": f"Contribuyente {i}", "domicilio": "Calle X"}
        for i in range(requerimientos_pdf.DUMMY_MAX_ROWS)
    ]
    pdf_path = tmp_path / "prueba.pdf"

    requerimientos_pdf.export_agente_pdf(
        pdf_path, agente=agente, abogado=abogado, rows=rows, filename="prueba.mcdiep",
        identity=requerimientos_pdf.dummy_identity(), dummy=True,
        watermark_text=f"PAE PRUEBA - {agente.full_name}",
    )

    assert pdf_path.exists()
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 1


# --- build_agente_envelope: private_key opcional --------------------------------------

def test_build_agente_envelope_without_private_key_is_unsigned(db):
    agente = _make_agente_dummy()
    abogado = _make_abogado()
    envelope = build_agente_envelope(
        [{"folio": "F-1", "cta_predial": "CP-1", "contribuyente": "X", "domicilio": "Y"}],
        agente=agente, abogado=abogado, private_key=None, document_uuid=requerimientos_pdf.DUMMY_LABEL,
    )
    assert envelope.signature is None
    assert envelope.signer_username == agente.username
    assert envelope.document_uuid == requerimientos_pdf.DUMMY_LABEL


def test_build_mandamiento_envelope_without_private_key_is_unsigned(db):
    agente = _make_agente_dummy()
    abogado = _make_abogado()
    envelope = build_mandamiento_envelope(
        [{"folio": "F-1", "cta_predial": "CP-1", "contribuyente": "X"}],
        agente=agente, abogado=abogado, private_key=None, document_uuid=mandamientos_pdf.DUMMY_LABEL,
    )
    assert envelope.signature is None


# --- RequerimientosGenerarView: exportación real de prueba, sin persistir en BD --------

def test_dummy_export_writes_real_files_without_db_writes(qapp, db, tmp_path):
    agente = _make_agente_dummy()
    _make_abogado()
    source_path = tmp_path / "lote.xlsx"
    _write_valid_requerimientos_file(source_path, rows=3)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    view = RequerimientosGenerarView(agente, dummy=True)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    # Seleccionar archivos no debe dejar rastro en el histórico de importados.
    assert req_repo.list_imported_files_for_agente(agente.id) == []

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    mcdiep_matches = list(dest_folder.glob("*.mcdiep"))
    pdf_matches = list(dest_folder.glob("*.pdf"))
    assert len(mcdiep_matches) == 1
    assert len(pdf_matches) == 1
    assert PdfReader(str(pdf_matches[0])).pages.__len__() == 1

    # Nada de esto debe haber quedado registrado en la base de datos.
    assert req_repo.list_batches_for_agente(agente.id) == []


def test_dummy_export_truncates_to_max_rows(qapp, db, tmp_path):
    agente = _make_agente_dummy()
    _make_abogado()
    source_path = tmp_path / "lote.xlsx"
    _write_valid_requerimientos_file(source_path, rows=requerimientos_pdf.DUMMY_MAX_ROWS + 5)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    view = RequerimientosGenerarView(agente, dummy=True)
    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()
    assert len(view._rows) == requerimientos_pdf.DUMMY_MAX_ROWS + 5

    with patch(
        "app.ui.agente.requerimientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch(
        "app.ui.agente.requerimientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.requerimientos_generar_view.QMessageBox.information"):
        view._on_export()

    pdf_matches = list(dest_folder.glob("*.pdf"))
    assert len(pdf_matches) == 1
    assert PdfReader(str(pdf_matches[0])).pages.__len__() == 1


def test_dummy_mandamiento_export_writes_real_files_without_db_writes(qapp, db, tmp_path):
    agente = _make_agente_dummy()
    _make_abogado()
    source_path = tmp_path / "lote.xlsx"
    _write_valid_mandamientos_file(source_path, rows=2)
    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()

    view = MandamientosGenerarView(agente, dummy=True)
    with patch(
        "app.ui.agente.mandamientos_generar_view.QFileDialog.getOpenFileNames",
        return_value=([str(source_path)], ""),
    ):
        view._on_select_files()

    with patch(
        "app.ui.agente.mandamientos_generar_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch(
        "app.ui.agente.mandamientos_generar_view.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("app.ui.agente.mandamientos_generar_view.QMessageBox.information"):
        view._on_export()

    assert len(list(dest_folder.glob("*.mcdiep"))) == 1
    assert len(list(dest_folder.glob("*.pdf"))) == 1
    assert mand_repo.list_batches_for_agente(agente.id) == []
