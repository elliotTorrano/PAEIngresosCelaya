"""Exportación del Formato de Requerimientos: Agente -> Abogado (.mcdiep, firmado
y atado a un Abogado) y Abogado -> Agente (.mcdiep, captura final). La revisión
del Agente (app/excel_io/requerimientos_export.py::export_revision) sigue
siendo un Excel normal -- es un documento de trabajo interno, no el intercambio
formal entre las dos partes."""

from __future__ import annotations

import uuid as uuid_module
from pathlib import Path

import openpyxl

from app.auth.crypto_certs import sign_challenge
from app.db.repositories.requerimientos import RequerimientoRow
from app.db.repositories.users import User
from app.excel_io import mcdiep_format

HEADERS_AGENTE = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"]
HEADERS_ABOGADO = HEADERS_AGENTE + [
    "Fecha de citatorio",
    "Recibe citatorio",
    "Nombre de quien recibe el citatorio",
    "Fecha de Notificación de citatorio",
    "Quién recibe el citatorio",
    "Nombre de quien recibe la notificación",
]
HEADERS_REVISION = HEADERS_ABOGADO + ["Procede", "ID Abogado"]


def build_agente_envelope(
    rows: list[dict], *, agente: User, abogado: User, private_key=None, document_uuid: str | None = None,
) -> mcdiep_format.McdiepEnvelope:
    """Arma (sin escribir a disco) el envelope firmado Agente -> Abogado --
    separado de `export_for_abogado` para poder calcular el hash/identidad
    del documento (ver app/pdf_io/requerimientos_pdf.py) antes de decidir el
    nombre del archivo final. `document_uuid` debe generarse ANTES de llamar
    (con app.pdf_io.requerimientos_pdf.new_document_uuid()) cuando quien
    exporta necesita ese mismo UUID para el PDF/nombre de archivo -- si se
    omite, se genera uno aquí (sólo para llamadas simples que no necesitan
    coordinarlo con nada más). `private_key=None` deja el envelope sin firmar
    -- sólo para las cuentas de prueba (agente_dummy, ver
    app/config.py::DUMMY_USERNAMES), que no tienen certificado; el flujo
    normal del Agente del PAE siempre pasa su certificado real."""
    payload = {
        "headers": HEADERS_AGENTE,
        "rows": [
            {
                "folio": row["folio"],
                "cta_predial": row["cta_predial"],
                "contribuyente": row["contribuyente"],
                "domicilio": row["domicilio"],
            }
            for row in rows
        ],
    }
    signable = mcdiep_format.signable_bytes(mcdiep_format.KIND_AGENTE_TO_ABOGADO, abogado.username, payload)
    signature = sign_challenge(private_key, signable) if private_key is not None else None

    return mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_AGENTE_TO_ABOGADO,
        signer_username=agente.username,
        target_username=abogado.username,
        payload=payload,
        signature=signature,
        document_uuid=document_uuid or str(uuid_module.uuid4()),
    )


def export_for_abogado(rows: list[dict], output_path: Path, *, agente: User, abogado: User, private_key) -> None:
    """Exporta lo importado por el Agente del PAE, listo para entregarle al
    Abogado: firmado con el certificado del Agente y atado a ese Abogado
    específico (ver app/excel_io/mcdiep_format.py) -- el Abogado no puede
    abrirlo con otra cuenta, ni editarlo a mano sin invalidar la firma."""
    envelope = build_agente_envelope(rows, agente=agente, abogado=abogado, private_key=private_key)
    mcdiep_format.write_envelope(output_path, envelope)


def build_abogado_envelope(rows: list[RequerimientoRow], *, document_uuid: str | None = None) -> mcdiep_format.McdiepEnvelope:
    """Arma (sin escribir a disco) el envelope Abogado -> Agente -- separado
    de `export_captured` por la misma razón que `build_agente_envelope`."""
    payload = {
        "headers": HEADERS_ABOGADO,
        "rows": [
            {
                "folio": row.folio,
                "cta_predial": row.cta_predial,
                "contribuyente": row.contribuyente,
                "domicilio": row.domicilio,
                "fecha_citatorio": row.fecha_citatorio,
                "recibe_citatorio": row.recibe_citatorio,
                "recibe_citatorio_nombre": row.recibe_citatorio_nombre,
                "fecha_notificacion": row.fecha_notificacion,
                "quien_recibe": row.quien_recibe,
                "quien_recibe_nombre": row.quien_recibe_nombre,
            }
            for row in rows
        ],
    }
    return mcdiep_format.McdiepEnvelope(
        kind=mcdiep_format.KIND_ABOGADO_TO_AGENTE,
        signer_username=None,
        target_username=None,
        payload=payload,
        signature=None,
        document_uuid=document_uuid or str(uuid_module.uuid4()),
    )


def export_captured(rows: list[RequerimientoRow], output_path: Path) -> None:
    """Exporta el resultado final capturado por el Abogado, para el Agente del
    PAE. No va firmado (el Abogado se autentica con contraseña, no tiene
    certificado), pero sigue siendo el contenedor .mcdiep -- no editable con
    Excel."""
    mcdiep_format.write_envelope(output_path, build_abogado_envelope(rows))


def export_revision(rows: list, output_path: Path) -> None:
    """Exporta la revisión del Agente (captura del Abogado + PROCEDE/NO PROCEDE).
    Documento de trabajo interno del Agente -- sigue siendo un Excel normal."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Revisión"
    sheet.append(HEADERS_REVISION)
    for row in rows:
        sheet.append(
            [
                row.folio,
                row.cta_predial,
                row.contribuyente,
                row.domicilio,
                row.fecha_citatorio,
                row.recibe_citatorio,
                row.recibe_citatorio_nombre,
                row.fecha_notificacion,
                row.quien_recibe,
                row.quien_recibe_nombre,
                row.procede,
                row.abogado_id,
            ]
        )
    workbook.save(output_path)
