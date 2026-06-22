"""Generador comercial de documentos para presupuestos guardados."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .catalog_repository import CatalogRepository
from .client_repository import ClientRepository
from .errors import JsonFileNotFoundError, RepositoryError, StoragePathError
from .storage import JsonStorage

try:  # pragma: no cover - la rama fallback se prueba forzando use_pdf=False.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except Exception:  # noqa: BLE001 - fallback documentado si la libreria no esta disponible.
    REPORTLAB_AVAILABLE = False

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class GeneratedDocument:
    presupuesto_id: str
    numero_comercial: str | None
    tipo_documento: str
    archivo: str
    ruta_relativa: str
    mensaje: str

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "presupuesto_id": self.presupuesto_id,
            "tipo_documento": self.tipo_documento,
            "archivo": self.archivo,
            "ruta_relativa": self.ruta_relativa,
            "mensaje": self.mensaje,
        }
        if self.numero_comercial:
            payload["numero_comercial"] = self.numero_comercial
        return payload


class CommercialDocumentGenerator:
    """Genera PDF real si reportlab existe; si no, HTML imprimible."""

    def __init__(self, storage: JsonStorage | None = None, *, use_pdf: bool | None = None):
        self.storage = storage or JsonStorage()
        self.use_pdf = REPORTLAB_AVAILABLE if use_pdf is None else use_pdf

    def generate(self, record: dict[str, Any]) -> GeneratedDocument:
        data = self._document_data(record)
        base_name = self.sanitize_filename(data["numero_visible"])
        extension = "pdf" if self.use_pdf else "html"
        relative_path = f"pdfs/{base_name}.{extension}"
        output_path = self.storage.resolve_path(relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.use_pdf:
            self._write_pdf(output_path, data)
            doc_type = "pdf"
            message = "Documento PDF comercial generado."
        else:
            self._write_html(output_path, data)
            doc_type = "html"
            message = "HTML imprimible generado como fallback."

        return GeneratedDocument(
            presupuesto_id=data["presupuesto_id"],
            numero_comercial=data.get("numero_comercial"),
            tipo_documento=doc_type,
            archivo=output_path.name,
            ruta_relativa=relative_path,
            mensaje=message,
        )

    @staticmethod
    def sanitize_filename(value: str) -> str:
        sanitized = _SAFE_FILENAME_PATTERN.sub("_", value.strip())
        sanitized = sanitized.strip("._")
        return sanitized or "presupuesto"

    @staticmethod
    def validate_document_filename(filename: str) -> None:
        if not isinstance(filename, str) or not filename:
            raise StoragePathError("archivo invalido.")
        if filename != Path(filename).name:
            raise StoragePathError("archivo invalido.")
        if filename != CommercialDocumentGenerator.sanitize_filename(filename):
            raise StoragePathError("archivo invalido.")
        if not (filename.endswith(".pdf") or filename.endswith(".html")):
            raise StoragePathError("extension de documento no soportada.")

    def _document_data(self, record: dict[str, Any]) -> dict[str, Any]:
        request = record.get("request") or {}
        result = record.get("result") or {}
        producto = request.get("producto") or {}
        costos_request = request.get("costos") or {}
        result_costs = result.get("costos") or {}
        result_production = result.get("produccion") or {}
        colores = producto.get("colores") or {}
        material = self._catalog_name("materiales", costos_request.get("material_id"))
        machine = self._catalog_name("maquinas", costos_request.get("maquina_id"))
        client = self._client_label(record)
        numero_comercial = record.get("numero_comercial")
        presupuesto_id = record.get("presupuesto_id") or "presupuesto"

        return {
            "presupuesto_id": presupuesto_id,
            "numero_comercial": numero_comercial,
            "numero_visible": numero_comercial or presupuesto_id,
            "fecha": record.get("created_at") or record.get("updated_at") or "",
            "cliente": client,
            "producto": producto.get("titulo") or producto.get("tipo") or "Trabajo offset",
            "cantidad": producto.get("cantidad", ""),
            "material": material or costos_request.get("material_id") or "",
            "maquina": machine or costos_request.get("maquina_id") or "",
            "colores": f"{colores.get('frente', 0)}/{colores.get('dorso', 0)}",
            "pliegos_buenos": result_production.get("pliegos_buenos", ""),
            "pliegos_brutos": result_production.get("pliegos_brutos", ""),
            "unidades_por_pliego": result_production.get("unidades_por_pliego", ""),
            "chapas": result_production.get("chapas", ""),
            "pasadas": result_production.get("pasadas", ""),
            "subtotal_tecnico": result_costs.get("costo_tecnico", ""),
            "margen": self._margin_label(result_costs, result_costs.get("moneda") or costos_request.get("moneda") or "PYG"),
            "impuesto": self._tax_label(result_costs, result_costs.get("moneda") or costos_request.get("moneda") or "PYG"),
            "precio_final": result_costs.get("precio_final", ""),
            "precio_unitario": result_costs.get("precio_unitario", ""),
            "moneda": result_costs.get("moneda") or costos_request.get("moneda") or "PYG",
            "observaciones": self._warnings_label(result.get("warnings") or []),
            "validez": "Documento comercial generado desde presupuesto guardado. Tarifas configurables o de ejemplo segun catalogos vigentes.",
        }

    def _catalog_name(self, tipo: str, item_id: str | None) -> str | None:
        if not item_id:
            return None
        try:
            catalog = CatalogRepository(self.storage).list_combined(tipo)
        except Exception:  # noqa: BLE001 - el documento debe poder generarse con IDs si catalogo falta.
            return None
        for item in catalog.get(tipo, []):
            if item.get("id") == item_id:
                return item.get("nombre") or item_id
        return None

    def _client_label(self, record: dict[str, Any]) -> str:
        request = record.get("request") or {}
        client_payload = request.get("cliente") or {}
        client_id = client_payload.get("cliente_id")
        if client_id:
            try:
                client = ClientRepository(self.storage).get_client(client_id)
                return client.get("empresa") or client.get("nombre") or client_id
            except (JsonFileNotFoundError, RepositoryError, StoragePathError):
                return client_id
        return client_payload.get("nombre") or ""

    @staticmethod
    def _margin_label(costs: dict[str, Any], currency: str) -> str:
        margin = costs.get("margen") or {}
        markup = costs.get("markup_pct")
        if isinstance(margin, dict) and margin.get("tipo"):
            return f"{margin.get('tipo')}: {margin.get('pct', '')}% / {CommercialDocumentGenerator._money(margin.get('monto', ''), currency)}"
        if markup:
            return f"markup: {markup}"
        return ""

    @staticmethod
    def _tax_label(costs: dict[str, Any], currency: str) -> str:
        taxes = costs.get("impuestos") or []
        if not taxes:
            return "Sin impuestos"
        labels = []
        for tax in taxes:
            labels.append(f"{tax.get('nombre', tax.get('id', 'impuesto'))}: {CommercialDocumentGenerator._money(tax.get('monto', ''), currency)}")
        return "; ".join(labels)

    @staticmethod
    def _warnings_label(warnings: list[dict[str, Any]]) -> str:
        if not warnings:
            return "Sin observaciones."
        return " | ".join(f"{item.get('code')}: {item.get('message')}" for item in warnings)

    def _write_pdf(self, path: Path, data: dict[str, Any]) -> None:
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
        story = [
            Paragraph("Presupuesto comercial", styles["Title"]),
            Paragraph(data["numero_visible"], styles["Heading2"]),
            Paragraph(f"Fecha: {data['fecha']}", styles["Normal"]),
            Spacer(1, 8),
        ]
        rows = [
            ("Presupuesto tecnico", data["presupuesto_id"]),
            ("Cliente", data["cliente"] or "No informado"),
            ("Producto", data["producto"]),
            ("Cantidad", data["cantidad"]),
            ("Material", data["material"]),
            ("Maquina", data["maquina"]),
            ("Colores frente/dorso", data["colores"]),
            ("Pliegos buenos", data["pliegos_buenos"]),
            ("Pliegos brutos", data["pliegos_brutos"]),
            ("Unidades por pliego", data["unidades_por_pliego"]),
            ("Chapas", data["chapas"]),
            ("Pasadas", data["pasadas"]),
            ("Subtotal tecnico", self._money(data["subtotal_tecnico"], data["moneda"])),
            ("Margen / markup", data["margen"] or "No informado"),
            ("Impuesto", data["impuesto"]),
            ("Precio final", self._money(data["precio_final"], data["moneda"])),
            ("Precio unitario", self._money(data["precio_unitario"], data["moneda"])),
            ("Observaciones", data["observaciones"]),
            ("Validez/configuracion", data["validez"]),
        ]
        table = Table([[Paragraph(str(label), styles["BodyText"]), Paragraph(str(value), styles["BodyText"])] for label, value in rows], colWidths=[48 * mm, 112 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f2")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#18211f")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8e0dd")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
        doc.build(story)

    def _write_html(self, path: Path, data: dict[str, Any]) -> None:
        rows = [
            ("Presupuesto tecnico", data["presupuesto_id"]),
            ("Cliente", data["cliente"] or "No informado"),
            ("Producto", data["producto"]),
            ("Cantidad", data["cantidad"]),
            ("Material", data["material"]),
            ("Maquina", data["maquina"]),
            ("Colores frente/dorso", data["colores"]),
            ("Pliegos buenos", data["pliegos_buenos"]),
            ("Pliegos brutos", data["pliegos_brutos"]),
            ("Unidades por pliego", data["unidades_por_pliego"]),
            ("Chapas", data["chapas"]),
            ("Pasadas", data["pasadas"]),
            ("Subtotal tecnico", self._money(data["subtotal_tecnico"], data["moneda"])),
            ("Margen / markup", data["margen"] or "No informado"),
            ("Impuesto", data["impuesto"]),
            ("Precio final", self._money(data["precio_final"], data["moneda"])),
            ("Precio unitario", self._money(data["precio_unitario"], data["moneda"])),
            ("Observaciones", data["observaciones"]),
            ("Validez/configuracion", data["validez"]),
        ]
        row_html = "\n".join(
            f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(str(value))}</td></tr>" for label, value in rows
        )
        content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{html.escape(data["numero_visible"])}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #18211f; margin: 32px; }}
    h1 {{ margin-bottom: 0; }}
    h2 {{ margin-top: 6px; color: #0f766e; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 24px; }}
    th, td {{ border: 1px solid #d8e0dd; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #eef3f2; width: 32%; }}
  </style>
</head>
<body>
  <h1>Presupuesto comercial</h1>
  <h2>{html.escape(data["numero_visible"])}</h2>
  <p>Fecha: {html.escape(str(data["fecha"]))}</p>
  <table>{row_html}</table>
</body>
</html>
"""
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _money(value: Any, currency: str) -> str:
        if value in (None, ""):
            return ""
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return f"{currency} {amount}"
        except (InvalidOperation, ValueError):
            return f"{currency} {value}"
