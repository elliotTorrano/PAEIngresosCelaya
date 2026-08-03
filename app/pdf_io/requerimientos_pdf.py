"""Genera el PDF de acompañamiento del Formato de Requerimientos -- se produce
junto al .mcdiep (mismo nombre, extensión .pdf) tanto en la exportación del
Agente del PAE (sin captura todavía) como en la del Abogado (ya capturado).

Horizontal, pensado para imprimirse a doble cara volteando por el lado largo
(bandera /Duplex /DuplexFlipLongEdge en las preferencias del visor -- una
sugerencia estándar del PDF, no todos los visores/impresoras la respetan).
Todas las columnas del cuerpo caben en el ancho de la hoja (el texto se
ajusta con salto de línea dentro de cada celda); las filas si son muchas
continúan en más páginas, repitiendo el encabezado de columnas.
"""

from __future__ import annotations

import base64
import hashlib
import uuid as uuid_module
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.auth.crypto_certs import sign_challenge
from app.config import QUIEN_RECIBE_EN_PUERTA, QUIEN_RECIBE_HOJA_CAMPO, QUIEN_RECIBE_NOMBRE
from app.db.repositories.requerimientos import RequerimientoRow
from app.db.repositories.users import User
from app.ui.widgets import theme
from app.ui.widgets.styles import login_background_path
from app.utils.filenames import sanitize_filename

PAGE_SIZE = landscape(letter)
MARGIN = 0.4 * inch
FOOTER_HEIGHT = 0.5 * inch
BOTTOM_MARGIN = FOOTER_HEIGHT + 0.15 * inch

HEADERS_AGENTE = ["FOLIO", "CTA PREDIAL", "CONTRIBUYENTE", "DOMICILIO"]
HEADERS_ABOGADO = HEADERS_AGENTE + [
    "Fecha de citatorio", "Recibe citatorio", "Nombre",
    "Fecha de notificación", "Quién recibe", "Nombre",
]

_styles = getSampleStyleSheet()
_STYLE_TITLE = ParagraphStyle("titulo", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER)
_STYLE_SUBTITLE = ParagraphStyle("subtitulo", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, alignment=TA_CENTER)
_STYLE_FORMATO = ParagraphStyle("formato", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER)
_STYLE_INFO = ParagraphStyle("info", parent=_styles["Normal"], fontName="Helvetica", fontSize=8.5, alignment=TA_LEFT)
_STYLE_COUNTER = ParagraphStyle("contador", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=9, alignment=TA_LEFT)
_STYLE_FIELD = ParagraphStyle("campo", parent=_styles["Normal"], fontName="Helvetica", fontSize=9, alignment=TA_LEFT)
_STYLE_CELL = ParagraphStyle("celda", parent=_styles["Normal"], fontName="Helvetica", fontSize=7, leading=8.5)
_STYLE_CELL_HEADER = ParagraphStyle("celda_encabezado", parent=_STYLE_CELL, fontName="Helvetica-Bold", textColor=colors.white)
_STYLE_STAMP = ParagraphStyle("sello", parent=_styles["Normal"], fontName="Helvetica", fontSize=8, leading=10)
_STYLE_STAMP_MONO = ParagraphStyle("sello_mono", parent=_STYLE_STAMP, fontName="Courier", fontSize=6.5, leading=8)
_STYLE_QR_LABEL = ParagraphStyle(
    "qr_etiqueta", parent=_styles["Normal"], fontName="Helvetica", fontSize=6, leading=7, alignment=TA_CENTER,
)


@dataclass
class DocumentIdentity:
    """Identificador del documento generado, al estilo del folio fiscal/sello
    digital de un CFDI del SAT: un UUID por exportación, el SHA-256 del
    .mcdiep ya escrito en disco, la marca de tiempo de la exportación y,
    sólo cuando hay certificado de por medio (flujo del Agente), la firma
    digital de ese hash."""

    uuid: str
    file_hash: str
    timestamp: datetime
    signature_b64: str | None


def new_document_uuid() -> str:
    """Genera el UUID de un documento nuevo -- se llama ANTES de construir el
    envelope (app.excel_io.requerimientos_export.build_agente_envelope /
    build_abogado_envelope), porque ese mismo UUID debe quedar embebido en el
    .mcdiep (para que quien lo importe lo pueda leer directamente) Y usarse
    después en `compute_identity` para el PDF/nombre de archivo -- un único
    UUID para las tres cosas, no uno distinto en cada lugar."""
    return str(uuid_module.uuid4())


def compute_identity(mcdiep_bytes: bytes, *, document_uuid: str, private_key=None) -> DocumentIdentity:
    """Calcula el hash (y la firma opcional) a partir de los bytes exactos ya
    escritos como .mcdiep -- `document_uuid` debe ser el mismo que ya quedó
    embebido en ese envelope (ver `new_document_uuid`), no uno nuevo."""
    file_hash = hashlib.sha256(mcdiep_bytes).hexdigest()
    signature_b64 = None
    if private_key is not None:
        signature_bytes = sign_challenge(private_key, file_hash.encode("utf-8"))
        signature_b64 = base64.b64encode(signature_bytes).decode("ascii")
    return DocumentIdentity(
        uuid=document_uuid, file_hash=file_hash,
        timestamp=datetime.now(), signature_b64=signature_b64,
    )


def suggested_filename(*, agente_nombre: str, abogado_nombre: str, identity: DocumentIdentity, extension: str) -> str:
    """Nombre sugerido para el .mcdiep (y su .pdf, con la misma base):
    AGENTE_ABOGADO_{primeros 8 del UUID}/{primeros 10 del hash} dd/mm/aaaa
    -- saneado para Windows, así que las diagonales de la plantilla quedan
    como guión bajo."""
    fecha = datetime.now().strftime("%d/%m/%Y")
    raw = f"{agente_nombre}_{abogado_nombre}_{identity.uuid[:8]}/{identity.file_hash[:10]} {fecha}"
    return sanitize_filename(raw) + extension


HEADER_ROW_COUNT = 8
HEADER_TABLE_HEIGHT = 2.0 * inch


def _compute_counts(quien_recibe_values: list[str | None], *, total_mode: str) -> dict[str, int]:
    """`instructivo`, `hoja_campo` y `notificado` son mutuamente excluyentes
    -- cada uno cuenta un valor exacto de QUIÉN RECIBE (EN PUERTA, HOJA DE
    CAMPO y NOMBRE respectivamente).

    `total_mode="all"` cuenta todas las filas del documento (exportación del
    Agente, antes de cualquier captura); `total_mode="filled"` cuenta sólo
    las que ya tienen un valor en QUIÉN RECIBE (exportación del Abogado)."""
    instructivo = sum(1 for v in quien_recibe_values if v == QUIEN_RECIBE_EN_PUERTA)
    hoja_campo = sum(1 for v in quien_recibe_values if v == QUIEN_RECIBE_HOJA_CAMPO)
    notificado = sum(1 for v in quien_recibe_values if v == QUIEN_RECIBE_NOMBRE)
    total = len(quien_recibe_values) if total_mode == "all" else sum(1 for v in quien_recibe_values if v)
    return {"total": total, "instructivo": instructivo, "hoja_campo": hoja_campo, "notificado": notificado}


HEADER_IMAGE_SCALE = 0.42  # deja espacio abajo para el QR de la primera página


def _header_image() -> Image:
    """Reutiliza el escudo del login (resources/login_background.png) como
    imagen izquierda de la cabecera, a un tamaño reducido dentro del espacio
    de las 10 filas."""
    path = login_background_path()
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    height = (HEADER_TABLE_HEIGHT - 10) * HEADER_IMAGE_SCALE
    width = height * (iw / ih)
    return Image(str(path), width=width, height=height)


def _build_header_table(
    available_width: float, *, abogado_nombre: str, counts: dict[str, int],
    include_notificacion_counters: bool, identity: DocumentIdentity,
    formato_titulo: str = "FORMATO: ENTREGA DE REQUERIMIENTOS DE PAGO",
) -> Table:
    fecha = datetime.now().strftime("%d/%m/%Y")
    counter_lines = []
    if include_notificacion_counters:
        counter_lines = [
            Paragraph(f"Notificado: {counts['notificado']}", _STYLE_COUNTER),
            Paragraph(f"Instructivo: {counts['instructivo']}", _STYLE_COUNTER),
            Paragraph(f"Hoja de campo: {counts['hoja_campo']}", _STYLE_COUNTER),
        ]
    counter_lines.append(Paragraph(f"Total de documentos a entregar: {counts['total']}", _STYLE_COUNTER))

    # Columna izquierda: el escudo y, debajo, el QR de esta primera página
    # (en las páginas siguientes el QR va al pie -- ver _make_footer_drawer).
    qr_payload = f"UUID: {identity.uuid[:8]}\nHash: {identity.file_hash[:10]}"
    left_cell = [
        _header_image(),
        Spacer(1, 4),
        _qr_drawing(qr_payload, 0.55 * inch),
        Paragraph(f"UUID: {identity.uuid[:8]}", _STYLE_QR_LABEL),
        Paragraph(f"Hash: {identity.file_hash[:10]}", _STYLE_QR_LABEL),
    ]

    data = [
        [left_cell, Paragraph("MUNICIPIO DE CELAYA GUANAJUATO", _STYLE_TITLE), ""],
        ["", Paragraph("TESORERÍA MUNICIPAL", _STYLE_SUBTITLE), ""],
        ["", Paragraph(formato_titulo, _STYLE_FORMATO), ""],
        ["", Paragraph("IMPUESTO PREDIAL", _STYLE_SUBTITLE), ""],
        ["", Paragraph("Dirección: Ingresos | Jefatura de Ejecución y Seguimiento", _STYLE_INFO), ""],
        ["", Paragraph("Procedimiento Administrativo de Ejecución", _STYLE_INFO), ""],
        ["", Paragraph(f"Despacho: {abogado_nombre}", _STYLE_FIELD), ""],
        ["", Paragraph(f"Fecha de elaboración: {fecha}", _STYLE_FIELD), ""],
    ]
    # Los contadores se apilan en la columna derecha, empezando en la fila 2
    # (a la altura de FORMATO) hacia abajo -- así no queda un hueco vacío
    # arriba ni se encima con el logo.
    for offset, line in enumerate(counter_lines):
        data[2 + offset][2] = line

    col_widths = [available_width * 0.20, available_width * 0.52, available_width * 0.28]
    table = Table(data, colWidths=col_widths, rowHeights=HEADER_TABLE_HEIGHT / HEADER_ROW_COUNT)
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, HEADER_ROW_COUNT - 1)),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (1, 0), (-1, -1), 6),
    ]))
    return table


def _column_weights(headers: list[str], table_rows: list[list[str]], sample_size: int = 200) -> list[float]:
    """Ancho proporcional a lo más largo visto en cada columna (encabezado o
    una muestra de filas), para que ninguna columna se corte y a la vez las
    columnas con texto corto (fechas, FOLIO) no desperdicien espacio."""
    sample = table_rows[:sample_size]
    weights = []
    for i, header in enumerate(headers):
        longest = len(header)
        for row in sample:
            cell = row[i] if i < len(row) else ""
            longest = max(longest, len(str(cell)))
        weights.append(max(longest, 4))
    return weights


def _build_body_table(available_width: float, headers: list[str], table_rows: list[list[str]]) -> Table:
    weights = _column_weights(headers, table_rows)
    total_weight = sum(weights)
    col_widths = [available_width * (w / total_weight) for w in weights]

    header_row = [Paragraph(h, _STYLE_CELL_HEADER) for h in headers]
    data = [header_row]
    for row in table_rows:
        data.append([Paragraph(str(cell) if cell is not None else "", _STYLE_CELL) for cell in row])

    # La paleta guardada del PDF -- independiente de la de interfaz y de
    # cualquier vista previa sin confirmar. Un documento oficial nunca debe
    # llevar un color que sólo se estaba probando en pantalla, ni cambiar
    # sólo porque alguien ajustó la interfaz a su gusto.
    header_color = theme.saved_pdf_colors()["critico"]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _qr_drawing(payload: str, size: float) -> Drawing:
    widget = qr.QrCodeWidget(payload)
    x1, y1, x2, y2 = widget.getBounds()
    w, h = x2 - x1, y2 - y1
    drawing = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    drawing.add(widget)
    return drawing


def _build_stamp_section(
    available_width: float, *, identity: DocumentIdentity, agente_nombre: str, abogado_nombre: str,
    filename: str,
) -> Table:
    """Sello del documento al estilo CFDI: QR a la izquierda (UUID, agente,
    archivo y los primeros 10 caracteres del hash) y, a un lado, el detalle
    en texto -- incluida la cadena de la firma cuando la exportación se hizo
    con certificado (flujo del Agente); si no, se indica que no hay firma."""
    qr_payload = (
        f"UUID: {identity.uuid}\n"
        f"Agente: {agente_nombre}\n"
        f"Archivo: {filename}\n"
        f"Hash: {identity.file_hash[:10]}"
    )
    qr_size = 0.85 * inch
    firma_texto = identity.signature_b64 or "Sin firma digital (exportación sin certificado)"

    info_cell = [
        Paragraph(f"<b>Agente:</b> {agente_nombre}", _STYLE_STAMP),
        Paragraph(f"<b>Abogado:</b> {abogado_nombre}", _STYLE_STAMP),
        Paragraph(f"<b>Archivo:</b> {filename}", _STYLE_STAMP),
        Paragraph(f"<b>UUID:</b> {identity.uuid}", _STYLE_STAMP),
        Paragraph(f"<b>Fecha y hora:</b> {identity.timestamp.strftime('%d/%m/%Y %H:%M:%S')}", _STYLE_STAMP),
        Paragraph(f"<b>Hash (SHA-256):</b> {identity.file_hash}", _STYLE_STAMP_MONO),
        Paragraph(f"<b>Firma digital del certificado:</b> {firma_texto}", _STYLE_STAMP_MONO),
    ]

    table = Table(
        [[_qr_drawing(qr_payload, qr_size), info_cell]],
        colWidths=[qr_size + 12, available_width - qr_size - 12],
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
    ]))
    return table


def _noop_page(canvas, doc) -> None:
    """La primera página no lleva marca al pie -- su QR ya va dentro del
    cuadro de la cabecera, debajo del escudo (ver _build_header_table)."""


def _make_footer_qr(identity: DocumentIdentity):
    """QR + identificadores cortos al pie, a la izquierda, en las páginas
    2 en adelante (la primera lleva su QR dentro de la cabecera)."""
    qr_payload = f"UUID: {identity.uuid[:8]}\nHash: {identity.file_hash[:10]}"
    qr_size = 0.42 * inch

    def _draw(canvas, doc) -> None:
        canvas.saveState()
        drawing = _qr_drawing(qr_payload, qr_size)
        x = doc.leftMargin
        y = (BOTTOM_MARGIN - qr_size) / 2
        renderPDF.draw(drawing, canvas, x, y)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(x + qr_size + 6, y + qr_size * 0.62, f"UUID: {identity.uuid[:8]}")
        canvas.drawString(x + qr_size + 6, y + qr_size * 0.18, f"Hash: {identity.file_hash[:10]}")
        canvas.restoreState()

    return _draw


def _apply_duplex_long_edge(pdf_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append(reader)
    prefs = writer.create_viewer_preferences()
    prefs[NameObject("/Duplex")] = NameObject("/DuplexFlipLongEdge")
    with open(pdf_path, "wb") as fh:
        writer.write(fh)


def _render_pdf(
    pdf_path: Path, *, agente_nombre: str, abogado_nombre: str, filename: str, headers: list[str],
    table_rows: list[list[str]], quien_recibe_values: list[str | None], total_mode: str,
    include_notificacion_counters: bool, identity: DocumentIdentity,
    formato_titulo: str = "FORMATO: ENTREGA DE REQUERIMIENTOS DE PAGO",
    documento_titulo: str = "Entrega de Requerimientos de Pago",
) -> None:
    counts = _compute_counts(quien_recibe_values, total_mode=total_mode)
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=PAGE_SIZE,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=BOTTOM_MARGIN,
        title=documento_titulo,
    )
    story = [
        _build_header_table(
            doc.width, abogado_nombre=abogado_nombre, counts=counts,
            include_notificacion_counters=include_notificacion_counters, identity=identity,
            formato_titulo=formato_titulo,
        ),
        Spacer(1, 10),
        _build_body_table(doc.width, headers, table_rows),
        Spacer(1, 10),
        _build_stamp_section(
            doc.width, identity=identity, agente_nombre=agente_nombre,
            abogado_nombre=abogado_nombre, filename=filename,
        ),
    ]
    doc.build(story, onFirstPage=_noop_page, onLaterPages=_make_footer_qr(identity))
    _apply_duplex_long_edge(pdf_path)


def export_agente_pdf(
    pdf_path: Path, *, agente: User, abogado: User, rows: list[dict], filename: str, identity: DocumentIdentity,
) -> None:
    """PDF que acompaña la exportación del Agente (export_for_abogado) --
    en esta etapa todavía no hay captura, así que sólo se muestra el total
    de documentos a entregar (la totalidad de las filas). Lleva firma digital
    real porque este flujo ya pide el certificado del Agente para firmar el
    .mcdiep -- `identity` debe venir de `compute_identity` con ese mismo
    certificado, calculada antes de escribir el .mcdiep (ver
    `suggested_filename`)."""
    table_rows = [
        [row["folio"] or "", row["cta_predial"] or "", row["contribuyente"] or "", row["domicilio"] or ""]
        for row in rows
    ]
    _render_pdf(
        pdf_path, agente_nombre=agente.full_name, abogado_nombre=abogado.full_name, filename=filename,
        headers=HEADERS_AGENTE, table_rows=table_rows, quien_recibe_values=[None] * len(rows),
        total_mode="all", include_notificacion_counters=False, identity=identity,
    )


def export_abogado_pdf(
    pdf_path: Path, *, agente: User, abogado: User, rows: list[RequerimientoRow], filename: str,
    identity: DocumentIdentity,
) -> None:
    """PDF que acompaña la exportación del Abogado (export_captured) -- ya
    con la captura de citatorio y notificación. El total de documentos a
    entregar sólo cuenta las filas con valor en QUIÉN RECIBE. Sin firma
    digital: el Abogado se autentica con contraseña, no tiene certificado
    (`identity` debe venir de `compute_identity(..., private_key=None)`)."""
    table_rows = [
        [
            row.folio or "", row.cta_predial or "", row.contribuyente or "", row.domicilio or "",
            row.fecha_citatorio or "", row.recibe_citatorio or "", row.recibe_citatorio_nombre or "",
            row.fecha_notificacion or "", row.quien_recibe or "", row.quien_recibe_nombre or "",
        ]
        for row in rows
    ]
    _render_pdf(
        pdf_path, agente_nombre=agente.full_name, abogado_nombre=abogado.full_name, filename=filename,
        headers=HEADERS_ABOGADO, table_rows=table_rows, quien_recibe_values=[row.quien_recibe for row in rows],
        total_mode="filled", include_notificacion_counters=True, identity=identity,
    )
