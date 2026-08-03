"""Exportación del Formato de Mandamientos: Agente -> Abogado (.mcdiep, firmado
y atado a un Abogado) y Abogado -> Agente (.mcdiep, captura final). Mismo
flujo que app/excel_io/requerimientos_export.py, sin la columna DOMICILIO
(el Excel de origen de Mandamiento no la trae)."""

from __future__ import annotations

import uuid as uuid_module
from pathlib import Path

import openpyxl

from app.auth.crypto_certs import sign_challenge
from app.db.repositories.mandamientos import MandamientoRow
from app.db.repositories.users import User
from app.excel_io import mcdiep_format

HEADERS_AGENTE = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE"]
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
    """Arma (sin escribir a disco) el envelope firmado Agente -> Abogado. Ver
    app/excel_io/requerimientos_export.py::build_agente_envelope. `private_key=None`
    deja el envelope sin firmar -- sólo para agente_dummy (sin certificado)."""
    payload = {
        "headers": HEADERS_AGENTE,
        "rows": [
            {
                "folio": row["folio"],
                "cta_predial": row["cta_predial"],
                "contribuyente": row["contribuyente"],
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


def export_agente_backup_xlsx(rows: list[dict], output_path: Path) -> None:
    """Respaldo en Excel de lo mismo que ya se exportó en .mcdiep/.pdf. Ver
    app/excel_io/requerimientos_export.py::export_agente_backup_xlsx."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Respaldo"
    sheet.append(HEADERS_AGENTE)
    for row in rows:
        sheet.append([row["folio"], row["cta_predial"], row["contribuyente"]])
    workbook.save(output_path)


def build_abogado_envelope(rows: list[MandamientoRow], *, document_uuid: str | None = None) -> mcdiep_format.McdiepEnvelope:
    """Arma (sin escribir a disco) el envelope Abogado -> Agente."""
    payload = {
        "headers": HEADERS_ABOGADO,
        "rows": [
            {
                "folio": row.folio,
                "cta_predial": row.cta_predial,
                "contribuyente": row.contribuyente,
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


def export_captured(rows: list[MandamientoRow], output_path: Path) -> None:
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
