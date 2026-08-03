"""Formato de archivo propio del sistema (.mcdiep) para el intercambio de
Requerimientos entre Agente del PAE y Abogado.

Es un contenedor binario -- no un Excel -- para que no se pueda editar a mano
con Excel ni con un editor de texto: cualquier alteración (incluso re-guardar
sin cambios reales desde otra herramienta) rompe el "framing" binario o
invalida la firma, y el programa se niega a abrirlo (ver requerimientos_import.py).

En el sentido Agente -> Abogado además va firmado con el certificado del
Agente (ver requerimientos_export.py/requerimientos_import.py, que usan este
módulo): la firma cubre el contenido Y el nombre de usuario del Abogado
destinatario, así que ni el contenido ni el destinatario pueden alterarse
después de firmado sin que la verificación falle.

No hay cifrado: la confidencialidad no es el objetivo (el contenido no es más
sensible que el Excel que reemplaza), sólo la integridad/autenticidad y que
no sea trivialmente editable en un programa de oficina común.
"""

from __future__ import annotations

import gzip
import json
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"MCDIEP01"
EXTENSION = ".mcdiep"

KIND_AGENTE_TO_ABOGADO = "agente_to_abogado"
KIND_ABOGADO_TO_AGENTE = "abogado_to_agente"

_LENGTH_STRUCT = struct.Struct(">I")


class InvalidMcdiepFile(Exception):
    """El archivo no tiene el formato .mcdiep esperado, o está dañado/incompleto."""


@dataclass
class McdiepEnvelope:
    kind: str
    signer_username: str | None  # quién firmó; None si el tipo no se firma
    target_username: str | None  # a quién va dirigido; None si no aplica
    payload: dict
    signature: bytes | None  # None si el tipo no se firma
    # Identificador del documento (ver app/pdf_io/requerimientos_pdf.py), el
    # mismo que se muestra en el PDF que se genera junto a este archivo --
    # va aquí para que quien IMPORTA el archivo (en otra máquina, sin acceso
    # a la base de datos de quien lo exportó) pueda leerlo directamente y
    # comparar contra el documento físico. No forma parte de lo que firma
    # `signable_bytes` -- es sólo un identificador, no contenido a proteger.
    document_uuid: str | None = None


def signable_bytes(kind: str, target_username: str | None, payload: dict) -> bytes:
    """Bytes exactos que se firman/verifican -- deterministas, para que se
    reconstruyan igual al firmar y al verificar."""
    canonical = {"kind": kind, "target_username": target_username, "payload": payload}
    return json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")


def envelope_bytes(envelope: McdiepEnvelope) -> bytes:
    """Serializa el envelope a los bytes exactos del archivo .mcdiep, sin
    escribir a disco -- para poder calcular un hash/identificador del
    documento ANTES de decidir dónde/cómo se llama el archivo final (ver
    app/pdf_io/requerimientos_pdf.py::compute_identity)."""
    header = {
        "kind": envelope.kind,
        "signer_username": envelope.signer_username,
        "target_username": envelope.target_username,
        "document_uuid": envelope.document_uuid,
    }
    header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
    payload_bytes = gzip.compress(json.dumps(envelope.payload, ensure_ascii=False).encode("utf-8"))
    signature_bytes = envelope.signature or b""

    out = bytearray()
    out += MAGIC
    out += _pack_field(header_bytes)
    out += _pack_field(signature_bytes)
    out += _pack_field(payload_bytes)
    return bytes(out)


def write_envelope(path: Path, envelope: McdiepEnvelope) -> None:
    path.write_bytes(envelope_bytes(envelope))


def read_envelope(path: Path) -> McdiepEnvelope:
    try:
        buf = path.read_bytes()
    except OSError as exc:
        raise InvalidMcdiepFile(f"No se pudo leer el archivo: {exc}") from exc

    if not buf.startswith(MAGIC):
        raise InvalidMcdiepFile(
            "El archivo no es un archivo .mcdiep válido de Sistema PAE (no tiene "
            "la marca de formato esperada). No se abre con Excel ni con otro "
            "programa -- sólo con Sistema PAE."
        )

    offset = len(MAGIC)
    header_bytes, offset = _unpack_field(buf, offset)
    signature_bytes, offset = _unpack_field(buf, offset)
    payload_bytes, offset = _unpack_field(buf, offset)

    try:
        header = json.loads(header_bytes.decode("utf-8"))
        payload = json.loads(gzip.decompress(payload_bytes).decode("utf-8"))
    except (ValueError, OSError) as exc:
        raise InvalidMcdiepFile(f"El archivo .mcdiep está dañado o fue alterado: {exc}") from exc

    return McdiepEnvelope(
        kind=header.get("kind"),
        signer_username=header.get("signer_username"),
        target_username=header.get("target_username"),
        payload=payload,
        signature=signature_bytes or None,
        document_uuid=header.get("document_uuid"),
    )


def _pack_field(data: bytes) -> bytes:
    return _LENGTH_STRUCT.pack(len(data)) + data


def _unpack_field(buf: bytes, offset: int) -> tuple[bytes, int]:
    if offset + _LENGTH_STRUCT.size > len(buf):
        raise InvalidMcdiepFile("El archivo .mcdiep está incompleto o dañado.")
    (length,) = _LENGTH_STRUCT.unpack(buf[offset : offset + _LENGTH_STRUCT.size])
    offset += _LENGTH_STRUCT.size
    if offset + length > len(buf):
        raise InvalidMcdiepFile("El archivo .mcdiep está incompleto o dañado.")
    return buf[offset : offset + length], offset + length
