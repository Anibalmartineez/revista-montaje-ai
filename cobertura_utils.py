import fitz
import numpy as np
from typing import Dict, Any


def calcular_metricas_cobertura(pdf_path: str, dpi: int = 72, umbral: int = 5) -> Dict[str, Any]:
    """Calcula métricas de cobertura CMYK y TAC de la primera página de un PDF.

    Devuelve un diccionario con:
        - ``cobertura_promedio``: porcentaje promedio de tinta por canal.
        - ``cobertura_por_area``: porcentaje del área con tinta en cada canal
          considerando un ``umbral`` mínimo.
        - ``cobertura_total``: porcentaje del área con presencia de tinta
          (cualquier canal sobre ``umbral``).
        - ``tac_p95``: percentil 95 del Total Area Coverage.
        - ``tac_max``: valor máximo del TAC.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix_cmyk = page.get_pixmap(matrix=mat, colorspace=fitz.csCMYK, alpha=False)
    pix_rgb = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
    doc.close()

    img_cmyk = np.frombuffer(pix_cmyk.samples, dtype=np.uint8).reshape(
        pix_cmyk.height, pix_cmyk.width, pix_cmyk.n
    ).astype(np.float32)
    img_rgb = np.frombuffer(pix_rgb.samples, dtype=np.uint8).reshape(
        pix_rgb.height, pix_rgb.width, pix_rgb.n
    )

    mask_white = (
        (img_rgb[..., 0] > 245)
        & (img_rgb[..., 1] > 245)
        & (img_rgb[..., 2] > 245)
    )
    img_cmyk[mask_white, :] = 0

    canales = ["Cyan", "Magenta", "Amarillo", "Negro"]
    cobertura_promedio = {
        canal: float(img_cmyk[:, :, i].mean() / 255.0 * 100.0)
        for i, canal in enumerate(canales)
    }
    cobertura_por_area = {
        canal: float((img_cmyk[:, :, i] > umbral).mean() * 100.0)
        for i, canal in enumerate(canales)
    }

    suma_cmyk = img_cmyk.sum(axis=2)
    cobertura_total = float((suma_cmyk > umbral).mean() * 100.0)
    tac_map = suma_cmyk / 255.0 * 100.0
    tac_p95 = float(np.percentile(tac_map, 95))
    tac_max = float(tac_map.max())

    return {
        "cobertura_promedio": cobertura_promedio,
        "cobertura_por_area": cobertura_por_area,
        "cobertura_total": cobertura_total,
        "tac_p95": tac_p95,
        "tac_max": tac_max,
    }
