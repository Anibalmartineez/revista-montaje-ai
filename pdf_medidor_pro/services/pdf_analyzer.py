"""Automatic PDF box analyzer for PDF Medidor Pro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from .geometry import rect_size_mm

BOX_KEYS = {
    "mediabox": "mediabox_mm",
    "cropbox": "cropbox_mm",
    "trimbox": "trimbox_mm",
    "bleedbox": "bleedbox_mm",
    "artbox": "artbox_mm",
}


def analyze_pdf_boxes(pdf_path: str | Path, page_index: int = 0) -> dict[str, Any]:
    """Read standard page boxes from a PDF and return dimensions in mm."""

    path = Path(pdf_path)
    with fitz.open(path) as doc:
        if doc.page_count < 1:
            raise ValueError("El PDF no contiene paginas.")
        if page_index < 0 or page_index >= doc.page_count:
            raise ValueError("La pagina solicitada no existe.")

        page = doc.load_page(page_index)
        boxes = _page_boxes(page)
        medidas_auto = {
            output_key: rect_size_mm(boxes.get(source_key))
            for source_key, output_key in BOX_KEYS.items()
        }

        return {
            "archivo": path.name,
            "pagina": page_index + 1,
            "page_count": doc.page_count,
            "medidas_auto": medidas_auto,
            "render_mm": rect_size_mm(page.rect),
        }


def _page_boxes(page: fitz.Page) -> dict[str, Any]:
    return {
        "mediabox": _safe_rect(page, "mediabox", fallback=page.rect),
        "cropbox": _safe_rect(page, "cropbox", fallback=page.rect),
        "trimbox": _safe_rect(page, "trimbox"),
        "bleedbox": _safe_rect(page, "bleedbox"),
        "artbox": _safe_rect(page, "artbox"),
    }


def _safe_rect(page: fitz.Page, attr: str, fallback: Any | None = None) -> Any | None:
    try:
        rect = getattr(page, attr)
    except Exception:
        return fallback
    if rect is None:
        return fallback
    if float(getattr(rect, "width", 0) or 0) <= 0:
        return fallback
    if float(getattr(rect, "height", 0) or 0) <= 0:
        return fallback
    return rect
