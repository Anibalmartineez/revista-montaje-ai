import os
import base64
import json
from io import BytesIO

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from ia_sugerencias import chat_completion


def diagnosticar_pdf(path):
    """Analiza un PDF y genera un diagnóstico técnico usando IA."""
    doc = fitz.open(path)
    first_page = doc[0]
    info = doc.metadata

    media = first_page.rect
    crop = first_page.cropbox or media
    bleed = first_page.bleedbox or crop
    art = first_page.artbox or crop

    contenido_dict = first_page.get_text("dict")
    drawings = first_page.get_drawings()
    page_width, page_height = media.width, media.height
    objetos_visibles = []
    marcas_corte = []

    def dentro_de_media(x0, y0, x1, y1):
        return 0 <= x0 <= page_width and 0 <= y0 <= page_height and 0 <= x1 <= page_width and 0 <= y1 <= page_height

    for d in drawings:
        ancho_linea = d.get("width", 0)
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
                if dentro_de_media(x0, y0, x1, y1):
                    if ancho_linea <= 0.3 and (x0 < 10 or x1 > page_width - 10 or y0 < 10 or y1 > page_height - 10):
                        marcas_corte.append((x0, y0, x1, y1))
                    else:
                        objetos_visibles.append((x0, y0, x1, y1))

    for img in first_page.get_images(full=True):
        try:
            bbox = first_page.get_image_bbox(img)
            if dentro_de_media(bbox.x0, bbox.y0, bbox.x1, bbox.y1):
                objetos_visibles.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
        except Exception:
            continue

    for bloque in contenido_dict.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            if dentro_de_media(x0, y0, x1, y1):
                objetos_visibles.append((x0, y0, x1, y1))

    if objetos_visibles:
        x_min = min(x0 for x0, _, _, _ in objetos_visibles)
        y_min = min(y0 for _, y0, _, _ in objetos_visibles)
        x_max = max(x1 for _, _, x1, _ in objetos_visibles)
        y_max = max(y1 for _, _, _, y1 in objetos_visibles)
        ancho_util_pt = x_max - x_min
        alto_util_pt = y_max - y_min
    else:
        ancho_util_pt = alto_util_pt = 0

    trim = first_page.trimbox if hasattr(first_page, "trimbox") and first_page.trimbox else None
    if not trim:
        if media.width > 600 and media.height > 100:
            margen_lateral = (media.width - 566.93) / 2
            margen_vertical = (media.height - 113.39) / 2
            trim = fitz.Rect(margen_lateral, margen_vertical,
                             media.width - margen_lateral, media.height - margen_vertical)
        else:
            trim = crop

    def pts_to_mm(v):
        return round(v * 25.4 / 72, 2)

    media_mm = (pts_to_mm(media.width), pts_to_mm(media.height))
    crop_mm = (pts_to_mm(crop.width), pts_to_mm(crop.height))
    trim_mm = (pts_to_mm(trim.width), pts_to_mm(trim.height))
    bleed_mm = (pts_to_mm(bleed.width), pts_to_mm(bleed.height))
    art_mm = (pts_to_mm(art.width), pts_to_mm(art.height))
    area_util_mm = (pts_to_mm(ancho_util_pt), pts_to_mm(alto_util_pt))

    advertencias = []
    if area_util_mm[0] > media_mm[0] or area_util_mm[1] > media_mm[1]:
        advertencias.append("❌ El contenido útil excede el tamaño de la página.")
    if area_util_mm[0] > trim_mm[0] or area_util_mm[1] > trim_mm[1]:
        advertencias.append("⚠️ El contenido útil es mayor que el área final de corte.")
    if area_util_mm[0] < trim_mm[0] * 0.9 or area_util_mm[1] < trim_mm[1] * 0.9:
        advertencias.append("⚠️ El contenido no ocupa completamente el área de corte final.")
    if not marcas_corte:
        advertencias.append("❌ No se detectaron marcas de corte.")
    else:
        advertencias.append(f"✅ Se detectaron {len(marcas_corte)} posibles marcas de corte.")

    dpi_info = "No se detectaron imágenes rasterizadas."
    image_list = first_page.get_images(full=True)
    if image_list:
        xref = image_list[0][0]
        base_image = doc.extract_image(xref)
        img_width = base_image["width"]
        img_height = base_image["height"]
        width_inch = media.width / 72
        height_inch = media.height / 72
        dpi_x = round(img_width / width_inch, 1)
        dpi_y = round(img_height / height_inch, 1)
        dpi_info = f"{dpi_x} x {dpi_y} DPI"

    tabla = f"""
📏 **Medidas del archivo (en milímetros):**

| Elemento                  | Ancho     | Alto      |
|--------------------------|-----------|-----------|
| Página (MediaBox)        | {media_mm[0]} mm | {media_mm[1]} mm |
| Corte Final (TrimBox)    | {trim_mm[0]} mm  | {trim_mm[1]} mm  |
| Sangrado (BleedBox)      | {bleed_mm[0]} mm | {bleed_mm[1]} mm |
| Área útil detectada      | {area_util_mm[0]} mm | {area_util_mm[1]} mm |
| Resolución estimada      | {dpi_info} |
"""

    observaciones = "\n".join(advertencias)
    prompt = f"""
Sos jefe de control de calidad en una imprenta. Evaluá el siguiente archivo PDF. Indicá si el diseño está bien armado para impresión: tamaño correcto, contenido bien ubicado, marcas de corte, resolución e indicaciones importantes para evitar errores.

{tabla}

🛠️ **Observaciones técnicas**:
{observaciones}
"""
    try:
        return chat_completion(prompt)
    except Exception as e:
        return f"[ERROR] No se pudo generar el diagnóstico con IA: {e}"


def analizar_grafico_tecnico(path_img):
    """Analiza un gráfico financiero detectando líneas y genera interpretación IA."""
    image = cv2.imread(path_img)
    if image is None:
        raise Exception("No se pudo leer la imagen.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    lineas_detectadas = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    lineas = []

    if lineas_detectadas is not None:
        for linea in lineas_detectadas[:20]:
            x1, y1, x2, y2 = map(int, linea[0])
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            lineas.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    buffer = BytesIO()
    img_pil.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    prompt = f"""
Eres un experto en análisis técnico bursátil. Se detectaron las siguientes líneas principales en un gráfico financiero (líneas de soporte, resistencia o tendencias). Basado en estas coordenadas (en formato de líneas con punto inicial y final):

{json.dumps(lineas, indent=2)}

Simula una breve interpretación como si fueras un analista técnico. Indica si se observa un canal, una tendencia, y si sería un buen momento para comprar, vender o esperar. Usa un tono profesional y claro.
"""
    try:
        resumen = chat_completion(prompt)
    except Exception as e:
        resumen = f"No se pudo generar el análisis técnico automático. Detalle: {str(e)}"

    return resumen, img_base64
