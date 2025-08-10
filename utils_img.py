import math


def dpi_for_preview(page_mm, max_pixels=10_000_000):
    # Preview ~110 dpi, pero limita a ~10MP
    target_dpi = 110
    w_in = page_mm[0] / 25.4
    h_in = page_mm[1] / 25.4
    est_px = w_in * h_in * target_dpi * target_dpi
    if est_px > max_pixels:
        scale = math.sqrt(max_pixels / est_px)
        target_dpi = max(72, int(target_dpi * scale))
    return target_dpi


def dpi_for_raster_ops(page_mm, max_pixels=12_000_000):
    # Fallback/sangrado ~240 dpi, techo ~12MP
    target_dpi = 240
    w_in = page_mm[0] / 25.4
    h_in = page_mm[1] / 25.4
    est_px = w_in * h_in * target_dpi * target_dpi
    if est_px > max_pixels:
        scale = math.sqrt(max_pixels / est_px)
        target_dpi = max(150, int(target_dpi * scale))
    return target_dpi

import os


def render_pdf_first_page_to_png(pdf_path: str, out_png: str, dpi: int = 150) -> None:
    """
    Intenta rasterizar con pdf2image (Poppler). Si falla o no está Poppler,
    hace fallback a PyMuPDF (fitz). No lanza excepción si no hay páginas.
    """
    # 1) Intento: pdf2image
    try:
        from pdf2image import convert_from_path  # import lazy
        imgs = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)
        if imgs:
            imgs[0].save(out_png)
            return
    except Exception as e:
        # Errores típicos sin Poppler:
        # - "Unable to get page count. Is poppler installed..."
        # - "No such file or directory: 'pdftoppm'"
        pass

    # 2) Fallback: PyMuPDF
    import fitz
    doc = fitz.open(pdf_path)
    if doc.page_count == 0:
        doc.close()
        return
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_png)
    doc.close()

