"""Lectura de los Excel del Formato de Requerimientos que sube el Agente del PAE.

Los archivos que llegan del origen no tienen un formato controlado por nosotros:
se omiten siempre las primeras 2 filas y la última, y se copian los datos libres
de las columnas B, C, D y F como FOLIO, CTA PREDIAL, CONTRIBUYENTE y DOMICILIO.

Se acepta tanto .xlsx/.xlsm (openpyxl) como .xls antiguo (xlrd) -- los archivos
de origen del padrón suelen venir en ese formato viejo.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from app.auth.crypto_certs import verify_challenge
from app.config import DUMMY_AGENTE_USERNAME
from app.db.repositories import users as users_repo
from app.db.repositories.users import User
from app.excel_io import mcdiep_format

COL_FOLIO = 2  # B
COL_CTA_PREDIAL = 3  # C
COL_CONTRIBUYENTE = 4  # D
COL_DOMICILIO = 6  # F

LEGACY_XLS_SUFFIXES = {".xls"}


class McdiepVerificationError(Exception):
    """El archivo .mcdiep no pasó la verificación de formato, firma o
    destinatario -- por diseño, no se abre en ninguno de estos casos."""


@dataclass
class ImportResult:
    filename: str
    rows: list[dict]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_requerimientos_file(path: Path) -> ImportResult:
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
                "domicilio": _value_text(row, COL_DOMICILIO),
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

    Verifica, en este orden: que sea un archivo .mcdiep del tipo correcto;
    que el firmante exista localmente y tenga certificado registrado; que la
    firma sea válida contra ESE certificado (cubre el contenido y el
    destinatario); y que el destinatario firmado sea exactamente `abogado`.
    Si cualquiera de estas verificaciones falla, no se abre -- se levanta
    McdiepVerificationError con el motivo.

    Excepción: si el firmante es exactamente `agente_dummy` (cuenta de
    prueba, ver app/config.py::DUMMY_AGENTE_USERNAME), se omiten las
    verificaciones de certificado/firma -- esa cuenta nunca tiene
    certificado (se autentica por contraseña) y su exportación de prueba
    (ver RequerimientosGenerarView, modo dummy) siempre queda sin firmar a
    propósito. La verificación de destinatario NO se omite: sigue siendo
    obligatoria para cualquier cuenta.

    Además del firmante, devuelve el UUID embebido en el archivo y el hash
    de los bytes tal como se recibieron -- el mismo identificador que trae
    el PDF que acompaña al .mcdiep, para comprobar visualmente que lo que se
    está importando concuerda con el documento físico."""
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    envelope = mcdiep_format.read_envelope(path)
    if envelope.kind != mcdiep_format.KIND_AGENTE_TO_ABOGADO:
        raise McdiepVerificationError(
            "Este archivo no es una lista de Requerimientos exportada por un Agente del PAE."
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
    Agente del PAE. No lleva firma (el Abogado no tiene certificado); sólo se
    verifica que sea un .mcdiep del tipo correcto. Igual que
    `parse_agente_export_file`, devuelve el UUID embebido y el hash de los
    bytes recibidos."""
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


def _read_all_row_values(path: Path) -> list[list]:
    """Devuelve todas las filas del archivo como listas de valores planos,
    sin importar si es .xls (xlrd) o .xlsx/.xlsm (openpyxl)."""
    if path.suffix.lower() in LEGACY_XLS_SUFFIXES:
        return _read_all_row_values_xls(path)
    return _read_all_row_values_xlsx(path)


def _read_all_row_values_xlsx(path: Path) -> list[list]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = workbook.active
        return [[cell.value for cell in row] for row in sheet.iter_rows()]
    finally:
        workbook.close()


def _read_all_row_values_xls(path: Path) -> list[list]:
    import xlrd

    workbook = xlrd.open_workbook(str(path))
    sheet = workbook.sheet_by_index(0)
    return [sheet.row_values(row_index) for row_index in range(sheet.nrows)]


def _is_row_empty(row: list) -> bool:
    return all(value in (None, "") for value in row)


def _value_text(row: list, col_index_1based: int) -> str | None:
    idx = col_index_1based - 1
    if idx >= len(row):
        return None
    value = row[idx]
    if value is None or value == "":
        return None
    return str(value).strip()


def _folio_text(row: list, col_index_1based: int) -> str | None:
    """Igual que `_value_text`, pero el folio es siempre un número entero:
    cuando Excel lo guarda como número (no como texto), openpyxl/xlrd lo
    devuelven como float (p. ej. 1234.0) y str() deja el ".0" a la vista."""
    idx = col_index_1based - 1
    if idx >= len(row):
        return None
    value = row[idx]
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
