"""Cuentas dummy en Revisar Formato y Captura del Abogado (v0.32.0): permiten
importar/capturar/exportar archivos reales, sin escribir nada en la base de
datos. Ver CHANGELOG.md 0.32.0 y el plan aprobado para el contexto completo."""

from unittest.mock import Mock, patch

from app.config import (
    AUTH_TYPE_PASSWORD,
    DUMMY_ABOGADO_USERNAME,
    DUMMY_AGENTE_USERNAME,
    ROLE_ABOGADO,
    ROLE_AGENTE_PAE,
)
from app.db.repositories import mandamientos as mand_repo
from app.db.repositories import requerimientos as req_repo
from app.db.repositories import revisiones as revisiones_repo
from app.db.repositories import revisiones_mandamiento as revisiones_mand_repo
from app.db.repositories import users as users_repo
from app.excel_io import mcdiep_format
from app.excel_io.mandamientos_export import build_agente_envelope as build_mand_agente_envelope
from app.excel_io.mandamientos_export import build_abogado_envelope as build_mand_abogado_envelope
from app.excel_io.mandamientos_import import McdiepVerificationError as MandVerificationError
from app.excel_io.mandamientos_import import parse_agente_export_file as parse_mand_agente_export_file
from app.excel_io.requerimientos_export import build_abogado_envelope, build_agente_envelope
from app.excel_io.requerimientos_import import McdiepVerificationError, parse_agente_export_file
from app.ui.abogado.mandamientos_capture_view import MandamientosCaptureView
from app.ui.abogado.requerimientos_capture_view import RequerimientosCaptureView
from app.ui.agente.mandamientos_revision_view import MandamientosRevisionView
from app.ui.agente.requerimientos_revision_view import RequerimientosRevisionView
from app.utils.paths import exports_dir


def _make_agente_dummy():
    return users_repo.create_user(
        username=DUMMY_AGENTE_USERNAME, role=ROLE_AGENTE_PAE, full_name="Agente del PAE (prueba)", email=None,
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_abogado_dummy():
    return users_repo.create_user(
        username=DUMMY_ABOGADO_USERNAME, role=ROLE_ABOGADO, full_name="Abogado de Prueba", email=None,
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


def _make_real_agente_no_cert(username="agente_sin_cert"):
    return users_repo.create_user(
        username=username, role=ROLE_AGENTE_PAE, full_name="Agente Sin Certificado", email="a@a.com",
        auth_type=AUTH_TYPE_PASSWORD, password_hash="x", password_salt="y",
    )


# --- excel_io: excepción de firma para el firmante dummy -----------------------------

def test_parse_agente_export_file_accepts_unsigned_dummy_signer(db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado = _make_abogado_dummy()
    envelope = build_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}],
        agente=agente_dummy, abogado=abogado, private_key=None,
    )
    path = tmp_path / "prueba.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    result = parse_agente_export_file(path, abogado=abogado)

    assert result.agente.username == DUMMY_AGENTE_USERNAME
    assert len(result.rows) == 1


def test_parse_agente_export_file_still_rejects_other_uncertified_signer(db, tmp_path):
    otro_agente = _make_real_agente_no_cert()
    abogado = _make_abogado_dummy()
    envelope = build_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}],
        agente=otro_agente, abogado=abogado, private_key=None,
    )
    path = tmp_path / "sin_firmar.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    raised = False
    try:
        parse_agente_export_file(path, abogado=abogado)
    except McdiepVerificationError:
        raised = True
    assert raised, "debía rechazar un firmante distinto de agente_dummy sin certificado"


def test_mand_parse_agente_export_file_accepts_unsigned_dummy_signer(db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado = _make_abogado_dummy()
    envelope = build_mand_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}],
        agente=agente_dummy, abogado=abogado, private_key=None,
    )
    path = tmp_path / "prueba.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    result = parse_mand_agente_export_file(path, abogado=abogado)

    assert result.agente.username == DUMMY_AGENTE_USERNAME
    assert len(result.rows) == 1


def test_mand_parse_agente_export_file_still_rejects_other_uncertified_signer(db, tmp_path):
    otro_agente = _make_real_agente_no_cert()
    abogado = _make_abogado_dummy()
    envelope = build_mand_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}],
        agente=otro_agente, abogado=abogado, private_key=None,
    )
    path = tmp_path / "sin_firmar.mcdiep"
    mcdiep_format.write_envelope(path, envelope)

    raised = False
    try:
        parse_mand_agente_export_file(path, abogado=abogado)
    except MandVerificationError:
        raised = True
    assert raised, "debía rechazar un firmante distinto de agente_dummy sin certificado"


# --- Captura del Abogado (dummy): importar/capturar/exportar real, sin BD ------------

def test_dummy_capture_full_flow_writes_real_files_without_db_rows(qapp, db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado_dummy = _make_abogado_dummy()

    source_path = tmp_path / "origen.mcdiep"
    envelope = build_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez", "domicilio": "Calle 1"}],
        agente=agente_dummy, abogado=abogado_dummy, private_key=None,
    )
    mcdiep_format.write_envelope(source_path, envelope)

    view = RequerimientosCaptureView(abogado_dummy, dummy=True)

    with patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getOpenFileName",
        return_value=(str(source_path), ""),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_import()

    assert view._current_batch_id == -1
    assert len(view._rows) == 1
    assert view._dummy_agente.username == DUMMY_AGENTE_USERNAME

    # Simula captura -- edición local directa, mismo patrón que el resto de la suite.
    view._rows[0].fecha_notificacion = "01/01/2024"
    view._rows[0].quien_recibe = "EN PUERTA"

    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()
    with patch(
        "app.ui.abogado.requerimientos_capture_view.RequerimientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch(
        "app.ui.abogado.requerimientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch("app.ui.abogado.requerimientos_capture_view.QMessageBox.information"):
        view._on_export()

    mcdiep_matches = list(dest_folder.glob("*.mcdiep"))
    pdf_matches = list(dest_folder.glob("*.pdf"))
    assert len(mcdiep_matches) == 1
    assert len(pdf_matches) == 1
    assert view._current_batch_finalizado is True
    assert view._dummy_exportado is True

    assert req_repo.list_batches_for_abogado(abogado_dummy.id) == []


def test_dummy_mandamiento_capture_full_flow_writes_real_files_without_db_rows(qapp, db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado_dummy = _make_abogado_dummy()

    source_path = tmp_path / "origen.mcdiep"
    envelope = build_mand_agente_envelope(
        [{"folio": "F-001", "cta_predial": "CP-001", "contribuyente": "Juan Pérez"}],
        agente=agente_dummy, abogado=abogado_dummy, private_key=None,
    )
    mcdiep_format.write_envelope(source_path, envelope)

    view = MandamientosCaptureView(abogado_dummy, dummy=True)

    with patch(
        "app.ui.abogado.mandamientos_capture_view.QFileDialog.getOpenFileName",
        return_value=(str(source_path), ""),
    ), patch("app.ui.abogado.mandamientos_capture_view.QMessageBox.information"):
        view._on_import()

    assert view._current_batch_id == -1
    assert len(view._rows) == 1

    view._rows[0].fecha_notificacion = "01/01/2024"
    view._rows[0].quien_recibe = "EN PUERTA"

    dest_folder = tmp_path / "destino"
    dest_folder.mkdir()
    with patch(
        "app.ui.abogado.mandamientos_capture_view.MandamientosCaptureView._ask_export_choice",
        return_value="only",
    ), patch(
        "app.ui.abogado.mandamientos_capture_view.QFileDialog.getExistingDirectory",
        return_value=str(dest_folder),
    ), patch("app.ui.abogado.mandamientos_capture_view.QMessageBox.information"):
        view._on_export()

    assert len(list(dest_folder.glob("*.mcdiep"))) == 1
    assert len(list(dest_folder.glob("*.pdf"))) == 1
    assert mand_repo.list_batches_for_abogado(abogado_dummy.id) == []


# --- Revisión del Agente (dummy): importar/marcar procede/exportar real, sin BD -------

def test_dummy_revision_full_flow_writes_real_file_without_db_rows(qapp, db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado_dummy = _make_abogado_dummy()

    row = req_repo.RequerimientoRow(
        id=1, batch_id=1, folio="F-001", cta_predial="CP-001", contribuyente="Juan Pérez",
        domicilio="Calle 1", fecha_citatorio="01/01/2024", recibe_citatorio="EN PUERTA",
        recibe_citatorio_nombre=None, fecha_notificacion="01/01/2024", quien_recibe="EN PUERTA",
        quien_recibe_nombre=None, observaciones="ok",
    )
    envelope = build_abogado_envelope([row], document_uuid="prueba-uuid")
    source_path = tmp_path / "captura_abogado.mcdiep"
    mcdiep_format.write_envelope(source_path, envelope)

    view = RequerimientosRevisionView(agente_dummy, dummy=True)
    view.abogado_combo.addItem(abogado_dummy.full_name, abogado_dummy.id)

    with patch(
        "app.ui.agente.requerimientos_revision_view.QFileDialog.getOpenFileName",
        return_value=(str(source_path), ""),
    ), patch("app.ui.agente.requerimientos_revision_view.QMessageBox.information"):
        view._on_import_revision()

    assert view._current_import_id == -1
    assert len(view._current_rows) == 1
    row_id = view._current_rows[0].id

    combo = Mock()
    combo.currentData.return_value = "PROCEDE"
    view._on_procede_changed(row_id, combo)
    assert view._current_rows[0].procede == "PROCEDE"

    with patch("app.ui.agente.requerimientos_revision_view.QMessageBox.information"):
        view._on_export_revision()

    matches = list(exports_dir().glob("REVISION DE PRUEBA DEL*.xlsx"))
    assert len(matches) == 1
    assert revisiones_repo.list_revision_imports(agente_dummy.id) == []


def test_dummy_mandamiento_revision_full_flow_writes_real_file_without_db_rows(qapp, db, tmp_path):
    agente_dummy = _make_agente_dummy()
    abogado_dummy = _make_abogado_dummy()

    row = mand_repo.MandamientoRow(
        id=1, batch_id=1, folio="F-001", cta_predial="CP-001", contribuyente="Juan Pérez",
        fecha_citatorio="01/01/2024", recibe_citatorio="EN PUERTA", recibe_citatorio_nombre=None,
        fecha_notificacion="01/01/2024", quien_recibe="EN PUERTA", quien_recibe_nombre=None,
        observaciones="ok",
    )
    envelope = build_mand_abogado_envelope([row], document_uuid="prueba-uuid")
    source_path = tmp_path / "captura_abogado.mcdiep"
    mcdiep_format.write_envelope(source_path, envelope)

    view = MandamientosRevisionView(agente_dummy, dummy=True)
    view.abogado_combo.addItem(abogado_dummy.full_name, abogado_dummy.id)

    with patch(
        "app.ui.agente.mandamientos_revision_view.QFileDialog.getOpenFileName",
        return_value=(str(source_path), ""),
    ), patch("app.ui.agente.mandamientos_revision_view.QMessageBox.information"):
        view._on_import_revision()

    assert view._current_import_id == -1
    assert len(view._current_rows) == 1
    row_id = view._current_rows[0].id

    combo = Mock()
    combo.currentData.return_value = "PROCEDE"
    view._on_procede_changed(row_id, combo)
    assert view._current_rows[0].procede == "PROCEDE"

    with patch("app.ui.agente.mandamientos_revision_view.QMessageBox.information"):
        view._on_export_revision()

    matches = list(exports_dir().glob("REVISION MANDAMIENTOS DE PRUEBA DEL*.xlsx"))
    assert len(matches) == 1
    assert revisiones_mand_repo.list_revision_imports(agente_dummy.id) == []
