"""Lectura de los Excel del Formato de Mandamientos que sube el Agente del PAE.

Mismo flujo que app/excel_io/requerimientos_import.py, con una diferencia: el
archivo de origen de Mandamiento sólo trae FOLIO, CTA PREDIAL y CONTRIBUYENTE
(columnas B, C y D) -- no hay DOMICILIO. Se omiten igual las primeras 2 filas
y la última.

Se acepta tanto .xlsx/.xlsm (openpyxl) como .xls antiguo (xlrd) -- los archivos
de origen del padrón suelen venir en ese formato viejo.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.auth.crypto_certs import verify_challenge
from app.config import DUMMY_AGENTE_USERNAME
from app.db.repositories import users as users_repo
from app.db.repositories.users import User
from app.excel_io import mcdiep_format
from app.excel_io.requerimientos_import import (
    McdiepVerificationError,
    _folio_text,
    _is_row_empty,
    _read_all_row_values,
    _value_text,
)

COL_FOLIO = 2  # B
COL_CTA_PREDIAL = 3  # C
COL_CONTRIBUYENTE = 4  # D


@dataclass
class ImportResult:
    filename: str
    rows: list[dict]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_mandamientos_file(path: Path) -> ImportResult:
    all_rows = _read_all_row_values(path)
    # Se omiten las 2 primeras filas y la última fila del archivo.
    data_rows = all_rows[2:-1] if len(all_rows) > 3 else []

    rows = []
    for row in data_rows:
        if _is_row_empty(row):
            continue
        rows.append(
            {
                "folio": _folio_text(row, COL_FOLIO),
                "cta_predial": _value_text(row, COL_CTA_PREDIAL),
                "contribuyente": _value_text(row, COL_CONTRIBUYENTE),
            }
        )
    return ImportResult(filename=path.name, rows=rows)


@dataclass
class AgenteImportResult:
    rows: list[dict]
    agente: User
    document_uuid: str | None
    file_hash: str


@dataclass
class AbogadoImportResult:
    rows: list[dict]
    document_uuid: str | None
    file_hash: str


def parse_agente_export_file(path: Path, *, abogado: User) -> AgenteImportResult:
    """Lee el archivo .mcdiep que el Agente del PAE exportó para `abogado`.
    Mismas verificaciones que requerimientos_import.py::parse_agente_export_file
    (tipo correcto, firmante con certificado registrado, firma válida,
    destinatario correcto -- con la misma excepción para el firmante
    `agente_dummy`) -- ver ese docstring para el detalle."""
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    envelope = mcdiep_format.read_envelope(path)
    if envelope.kind != mcdiep_format.KIND_AGENTE_TO_ABOGADO:
        raise McdiepVerificationError(
            "Este archivo no es una lista de Mandamientos exportada por un Agente del PAE."
        )

    signer = users_repo.get_by_username(envelope.signer_username or "")
    is_dummy_signer = envelope.signer_username == DUMMY_AGENTE_USERNAME
    if signer is None or (not is_dummy_signer and not signer.cert_public_pem):
        raise McdiepVerificationError(
            f"El archivo dice estar firmado por '{envelope.signer_username}', pero esa cuenta "
            "no existe o no tiene un certificado registrado en esta instalación."
        )

    if not is_dummy_signer:
        signable = mcdiep_format.signable_bytes(envelope.kind, envelope.target_username, envelope.payload)
        if not envelope.signature or not verify_challenge(signer.cert_public_pem, signable, envelope.signature):
            raise McdiepVerificationError(
                "La firma de este archivo no es válida: el contenido pudo haber sido alterado "
                "después de firmarse, o el certificado del firmante ya no es el mismo."
            )

    if envelope.target_username != abogado.username:
        raise McdiepVerificationError(
            f"Este archivo fue firmado para el Abogado '{envelope.target_username}', no para "
            f"'{abogado.username}'. No se abre."
        )

    return AgenteImportResult(
        rows=envelope.payload.get("rows", []), agente=signer,
        document_uuid=envelope.document_uuid, file_hash=file_hash,
    )


def parse_abogado_export_file(path: Path) -> AbogadoImportResult:
    """Lee el archivo .mcdiep que el Abogado exportó con su captura, para el
    Agente del PAE. Ver requerimientos_import.py::parse_abogado_export_file."""
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    envelope = mcdiep_format.read_envelope(path)
    if envelope.kind != mcdiep_format.KIND_ABOGADO_TO_AGENTE:
        raise McdiepVerificationError(
            "Este archivo no es una captura de Abogado exportada por Sistema PAE."
        )
    return AbogadoImportResult(
        rows=envelope.payload.get("rows", []), document_uuid=envelope.document_uuid, file_hash=file_hash,
    )
