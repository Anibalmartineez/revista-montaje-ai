"""Preview rendering for PDF Medidor Pro."""

from __future__ import annotations

from pathlib import Path

import fitz

from .geometry import rect_size_mm


def render_first_page(
    pdf_path: str | Path,
    output_path: str | Path,
    dpi: int = 150,
) -> dict[str, object]:
    """Render the first PDF page to a PNG image."""
    return render_page(pdf_path, output_path, page_index=0, dpi=dpi)


def render_page(
    pdf_path: str | Path,
    output_path: str | Path,
    page_index: int = 0,
    dpi: int = 150,
) -> dict[str, object]:
    """Render a PDF page to a PNG image."""

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as doc:
        if doc.page_count < 1:
            raise ValueError("El PDF no contiene paginas.")
        if page_index < 0 or page_index >= doc.page_count:
            raise ValueError("La pagina solicitada no existe.")
        page = doc.load_page(page_index)
        zoom = float(dpi) / 72.0
        pix = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            alpha=False,
            colorspace=fitz.csRGB,
        )
        pix.save(output_path)
        return {
            "filename": output_path.name,
            "width_px": int(pix.width),
            "height_px": int(pix.height),
            "dpi": int(dpi),
            "render_mm": rect_size_mm(page.rect),
        }
