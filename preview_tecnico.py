import os
import uuid
import fitz
import numpy as np
from PIL import Image, ImageDraw
from flask import current_app


def generar_preview_tecnico(pdf_path: str, datos_formulario: dict, dpi: int = 200) -> str:
    """Genera una imagen con advertencias técnicas.

    Renderiza la primera página del PDF y resalta:
    - Zonas con tramas < 5% (azul)
    - Textos < 4 pt (naranja)
    - Cobertura de tinta > 90% (rojo)
    - Elementos en RGB u otros espacios de color no CMYK (gris oscuro)

    Devuelve la ruta relativa dentro de ``static`` donde se guardó la imagen.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Análisis de pixeles en CMYK
    img_cmyk = img.convert("CMYK")
    arr = np.array(img_cmyk)
    h, w = arr.shape[:2]
    overlay = np.zeros((h, w, 4), dtype=np.uint8)

    # 🔵 Tramas <5%
    weak_mask = ((arr > 0) & (arr < 13)).any(axis=2)
    overlay[weak_mask] = [0, 0, 255, 120]

    # 🔴 Cobertura >90%
    coverage = arr.sum(axis=2) / (255 * 4)
    high_mask = coverage > 0.9
    overlay[high_mask] = [255, 0, 0, 120]

    img_rgba = img.convert("RGBA")
    overlay_img = Image.fromarray(overlay, "RGBA")
    composed = Image.alpha_composite(img_rgba, overlay_img)
    draw = ImageDraw.Draw(composed)

    text_data = page.get_text("dict")
    # 🟠 Textos <4 pt y ⚫ Elementos no CMYK
    for block in text_data.get("blocks", []):
        btype = block.get("type")
        if btype == 0:  # texto
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("size", 0) < 4:
                        x0, y0, x1, y1 = span["bbox"]
                        rect = [x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom]
                        draw.rectangle(rect, outline=(255, 165, 0, 255), width=2)
        elif btype == 1:  # imagen
            x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
            xref = block.get("image")
            cs = ""
            if xref:
                try:
                    info = doc.extract_image(xref)
                    cs = info.get("colorspace", "")
                except Exception:
                    cs = ""
            if cs and cs.upper() != "CMYK":
                rect = [x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom]
                draw.rectangle(rect, fill=(64, 64, 64, 120))

    doc.close()

    static_dir = getattr(current_app, "static_folder", "static")
    previews_dir = os.path.join(static_dir, "previews")
    os.makedirs(previews_dir, exist_ok=True)
    filename = f"preview_tecnico_{uuid.uuid4().hex}.png"
    output_abs = os.path.join(previews_dir, filename)
    composed.save(output_abs)

    return os.path.join("previews", filename)
