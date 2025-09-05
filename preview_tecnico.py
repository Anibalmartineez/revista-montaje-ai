import os
import uuid
import fitz
import numpy as np
import tempfile
from PIL import Image, ImageDraw
from flask import current_app


def analizar_riesgos_pdf(pdf_path: str, dpi: int = 200) -> dict:
    """Analiza el PDF y genera una imagen de superposición con zonas de riesgo.

    Devuelve un diccionario con la ruta absoluta de dicha superposición y el
    ``dpi`` utilizado, para reutilizarla luego sin recalcular el diagnóstico.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

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

    overlay_img = Image.fromarray(overlay, "RGBA")
    draw = ImageDraw.Draw(overlay_img)

    text_data = page.get_text("dict")
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
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    overlay_img.save(tmp.name)
    return {"overlay_path": tmp.name, "dpi": dpi}


def generar_preview_tecnico(
    pdf_path: str,
    datos_formulario: dict | None,
    overlay_path: str | None = None,
    dpi: int = 200,
) -> str:
    """Genera una vista previa técnica reutilizando los datos de diagnóstico.

    Si ``overlay_path`` está definido, se utiliza la superposición previamente
    calculada; de lo contrario, se genera una imagen vacía (sin advertencias).
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    base = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

    if overlay_path and os.path.exists(overlay_path):
        overlay_img = Image.open(overlay_path).convert("RGBA")
    else:
        overlay_img = Image.new("RGBA", base.size, (0, 0, 0, 0))

    composed = Image.alpha_composite(base, overlay_img)
    doc.close()

    static_dir = getattr(current_app, "static_folder", "static")
    previews_dir = os.path.join(static_dir, "previews")
    os.makedirs(previews_dir, exist_ok=True)
    filename = f"preview_tecnico_{uuid.uuid4().hex}.png"
    output_abs = os.path.join(previews_dir, filename)
    composed.save(output_abs)

    return os.path.join("previews", filename)
