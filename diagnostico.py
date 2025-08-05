import base64
import json
from io import BytesIO

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from ia_sugerencias import chat_completion


def pts_to_mm(v):
    """Convierte puntos tipográficos a milímetros."""
    return round(v * 25.4 / 72, 2)


def agrupar_bboxes(bboxes, margen=0):
    """Agrupa cajas que se superponen para detectar objetos independientes."""
    clusters = []
    for box in bboxes:
        merged = False
        for i, cl in enumerate(clusters):
            if not (box[2] < cl[0] - margen or box[0] > cl[2] + margen or box[3] < cl[1] - margen or box[1] > cl[3] + margen):
                clusters[i] = (
                    min(cl[0], box[0]),
                    min(cl[1], box[1]),
                    max(cl[2], box[2]),
                    max(cl[3], box[3]),
                )
                merged = True
                break
        if not merged:
            clusters.append(box)

    changed = True
    while changed:
        changed = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, b = clusters[i], clusters[j]
                if not (a[2] < b[0] - margen or a[0] > b[2] + margen or a[3] < b[1] - margen or a[1] > b[3] + margen):
                    clusters[i] = (
                        min(a[0], b[0]),
                        min(a[1], b[1]),
                        max(a[2], b[2]),
                        max(a[3], b[3]),
                    )
                    clusters.pop(j)
                    changed = True
                    break
            if changed:
                break
    return clusters


def detectar_marcas_corte(page, margen=15):
    """Detecta marcas de corte y retorna el área interna entre ellas."""
    drawings = page.get_drawings()
    width, height = page.rect.width, page.rect.height
    marcas = {"left": [], "right": [], "top": [], "bottom": []}
    objetos = []

    for d in drawings:
        wline = d.get("width", 0)
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
                minx, miny = min(x0, x1), min(y0, y1)
                maxx, maxy = max(x0, x1), max(y0, y1)

                if wline <= 0.5 and abs(x0 - x1) < 0.5 and abs(y1 - y0) > 5:
                    if minx < 0 and 0 <= maxx <= margen:
                        marcas["left"].append(maxx)
                    elif maxx > width and width - margen <= minx <= width:
                        marcas["right"].append(minx)
                    else:
                        objetos.append((minx, miny, maxx, maxy))
                elif wline <= 0.5 and abs(y0 - y1) < 0.5 and abs(x1 - x0) > 5:
                    if miny < 0 and 0 <= maxy <= margen:
                        marcas["top"].append(maxy)
                    elif maxy > height and height - margen <= miny <= height:
                        marcas["bottom"].append(miny)
                    else:
                        objetos.append((minx, miny, maxx, maxy))
                else:
                    objetos.append((minx, miny, maxx, maxy))
            else:
                bbox = d.get("bbox")
                if bbox:
                    objetos.append(bbox)

    rect = None
    if all(marcas.values()):
        rect = fitz.Rect(
            max(marcas["left"]),
            max(marcas["top"]),
            min(marcas["right"]),
            min(marcas["bottom"]),
        )

    num_marks = sum(len(v) for v in marcas.values())
    return rect, objetos, num_marks


def obtener_bboxes(page, extra_drawings):
    """Obtiene todas las cajas visibles (texto, imágenes, etc.)."""
    width, height = page.rect.width, page.rect.height
    bboxes = list(extra_drawings)

    def dentro(x0, y0, x1, y1):
        return not (x1 < 0 or x0 > width or y1 < 0 or y0 > height)

    for img in page.get_images(full=True):
        try:
            bbox = page.get_image_bbox(img)
            if dentro(bbox.x0, bbox.y0, bbox.x1, bbox.y1):
                bboxes.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
        except Exception:
            pass

    contenido = page.get_text("rawdict")
    for bloque in contenido.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            if dentro(x0, y0, x1, y1):
                bboxes.append((x0, y0, x1, y1))

    return bboxes


def diagnosticar_pdf(path):
    """Analiza un PDF y genera un diagnóstico técnico usando IA."""
    doc = fitz.open(path)
    page = doc[0]

    media = page.rect
    crop = page.cropbox or media
    bleed = page.bleedbox or crop
    trim = page.trimbox if page.trimbox else crop

    rect_corte, dibujos_objetos, marcas_detectadas = detectar_marcas_corte(page)
    bboxes = obtener_bboxes(page, dibujos_objetos)
    clusters = agrupar_bboxes(bboxes)

    if clusters:
        union_rect = fitz.Rect(
            min(b[0] for b in clusters),
            min(b[1] for b in clusters),
            max(b[2] for b in clusters),
            max(b[3] for b in clusters),
        )
    else:
        union_rect = fitz.Rect(0, 0, 0, 0)

    area_final = rect_corte or union_rect

    media_mm = (pts_to_mm(media.width), pts_to_mm(media.height))
    trim_mm = (pts_to_mm(area_final.width), pts_to_mm(area_final.height))
    contenido_mm = (pts_to_mm(union_rect.width), pts_to_mm(union_rect.height))
    bleed_mm = (pts_to_mm(bleed.width), pts_to_mm(bleed.height))

    advertencias = []
    if rect_corte is None:
        advertencias.append("❌ No se detectaron marcas de corte.")
    else:
        advertencias.append(f"✅ Se detectaron {marcas_detectadas} marcas de corte.")

    if union_rect.x0 < 0 or union_rect.y0 < 0 or union_rect.x1 > media.x1 or union_rect.y1 > media.y1:
        advertencias.append("❌ El contenido útil excede el tamaño de la página.")
    if rect_corte and (
        union_rect.x0 < rect_corte.x0
        or union_rect.y0 < rect_corte.y0
        or union_rect.x1 > rect_corte.x1
        or union_rect.y1 > rect_corte.y1
    ):
        advertencias.append("⚠️ El contenido se extiende fuera del área de corte.")
    if len(clusters) > 1:
        advertencias.append(
            f"⚠️ Se detectaron {len(clusters)} objetos independientes en la página."
        )

    objetos_descript = []
    for i, cl in enumerate(clusters, 1):
        w_mm = pts_to_mm(cl[2] - cl[0])
        h_mm = pts_to_mm(cl[3] - cl[1])
        objetos_descript.append(f"Objeto {i}: {w_mm} x {h_mm} mm")
        if rect_corte and not rect_corte.contains(fitz.Rect(cl)):
            advertencias.append(f"⚠️ El objeto {i} sobresale del área útil.")

    objetos_resumen = "\n".join(objetos_descript) if objetos_descript else "Sin objetos detectados."

    dpi_list = []
    for img in page.get_images(full=True):
        try:
            bbox = page.get_image_bbox(img)
            pix = doc.extract_image(img[0])
            w_px, h_px = pix["width"], pix["height"]
            dpi_x = w_px / (bbox.width / 72)
            dpi_y = h_px / (bbox.height / 72)
            dpi = min(dpi_x, dpi_y)
            dpi_list.append(dpi)
            if dpi < 300:
                advertencias.append(
                    f"⚠️ Imagen con baja resolución ({round(dpi)} DPI)."
                )
        except Exception:
            continue

    if dpi_list:
        dpi_info = ", ".join(f"{round(d)} DPI" for d in dpi_list)
    else:
        dpi_info = "No se detectaron imágenes rasterizadas."

    tabla = f"""
📏 **Medidas del archivo (en milímetros):**

| Elemento                  | Ancho     | Alto      |
|--------------------------|-----------|-----------|
| Página (MediaBox)        | {media_mm[0]} mm | {media_mm[1]} mm |
| Área final estimada      | {trim_mm[0]} mm | {trim_mm[1]} mm |
| Área ocupada por contenido| {contenido_mm[0]} mm | {contenido_mm[1]} mm |
| Sangrado (BleedBox)      | {bleed_mm[0]} mm | {bleed_mm[1]} mm |
| Resolución estimada      | {dpi_info} |
"""

    observaciones = "\n".join(advertencias)

    prompt = f"""
Sos jefe de control de calidad en una imprenta. Evaluá el siguiente archivo PDF. Indicá si el diseño está bien armado para impresión: tamaño correcto, contenido bien ubicado, marcas de corte, resolución e indicaciones importantes para evitar errores.

{tabla}

📦 **Objetos detectados:**
{objetos_resumen}

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

    lineas_detectadas = cv2.HoughLinesP(
        edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10
    )
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

