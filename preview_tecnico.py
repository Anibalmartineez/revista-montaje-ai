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

    # 🔵 Tramas <5% por canal
    c_mask = (arr[:, :, 0] > 0) & (arr[:, :, 0] < 13)
    m_mask = (arr[:, :, 1] > 0) & (arr[:, :, 1] < 13)
    y_mask = (arr[:, :, 2] > 0) & (arr[:, :, 2] < 13)
    k_mask = (arr[:, :, 3] > 0) & (arr[:, :, 3] < 13)
    overlay[c_mask] = [0, 255, 255, 120]  # Cian
    overlay[m_mask] = [255, 0, 255, 120]  # Magenta
    overlay[y_mask] = [255, 255, 0, 120]  # Amarillo
    overlay[k_mask] = [0, 0, 0, 120]      # Negro débil

    # 🔴 Cobertura >90%
    coverage = arr.sum(axis=2) / (255 * 4)
    high_mask = coverage > 0.9
    overlay[high_mask] = [255, 0, 0, 120]

    overlay_img = Image.fromarray(overlay, "RGBA")
    draw = ImageDraw.Draw(overlay_img)

    text_data = page.get_text("dict")
    sangrado_mm = 3
    sangrado_pts = sangrado_mm * 72 / 25.4
    contenido_cerca_borde = False

    for block in text_data.get("blocks", []):
        btype = block.get("type")
        if btype == 0:  # texto
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    x0, y0, x1, y1 = span["bbox"]
                    if span.get("size", 0) < 4:
                        rect = [x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom]
                        draw.rectangle(rect, outline=(255, 0, 0, 255), width=2)
                    margen_min = min(x0, page.rect.width - x1, y0, page.rect.height - y1)
                    if margen_min < sangrado_pts:
                        contenido_cerca_borde = True
        elif btype == 1:  # imagen
            x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
            margen_min = min(x0, page.rect.width - x1, y0, page.rect.height - y1)
            if margen_min < sangrado_pts:
                contenido_cerca_borde = True
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

    # Línea de sangrado (azul si correcto, rojo si insuficiente)
    rect_segura = [
        sangrado_pts * zoom,
        sangrado_pts * zoom,
        (page.rect.width - sangrado_pts) * zoom,
        (page.rect.height - sangrado_pts) * zoom,
    ]
    color_sangrado = (255, 0, 0, 255) if contenido_cerca_borde else (0, 0, 255, 255)
    draw.rectangle(rect_segura, outline=color_sangrado, width=3)

    doc.close()
    tmp_dir = tempfile.gettempdir()
    filename = f"preview_tecnico_overlay_{uuid.uuid4().hex}.png"
    tmp_path = os.path.join(tmp_dir, filename)
    overlay_img.save(tmp_path)
    return {"overlay_path": tmp_path, "dpi": dpi}


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
    filename = f"preview_tecnico_overlay_{uuid.uuid4().hex}.png"
    output_abs = os.path.join(previews_dir, filename)
    composed.save(output_abs)

    return os.path.join("previews", filename)
