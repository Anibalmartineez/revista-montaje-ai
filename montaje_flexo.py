import fitz  # PyMuPDF
import os
import numpy as np
from pdf2image import convert_from_path
import cv2

def revisar_diseño_flexo(path_pdf, anilox_lpi, paso_mm):
    doc = fitz.open(path_pdf)
    pagina = doc[0]
    media = pagina.rect
    contenido = pagina.get_text("dict")
    advertencias = []

    # Medidas del diseño en mm
    ancho_mm = round(media.width * 25.4 / 72, 2)
    alto_mm = round(media.height * 25.4 / 72, 2)

    if alto_mm > paso_mm:
        advertencias.append(f"❌ El alto del diseño ({alto_mm} mm) es mayor al paso del cilindro ({paso_mm} mm).")

    for bloque in contenido.get("blocks", []):
        if "lines" in bloque:
            for l in bloque["lines"]:
                for s in l["spans"]:
                    size = s.get("size", 0)
                    if size < 4:
                        advertencias.append(f"⚠️ Texto pequeño detectado: '{s['text']}' ({round(size, 1)} pt). Riesgo de pérdida en impresión.")
        elif "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            w = x1 - x0
            h = y1 - y0
            if w < 1 or h < 1:
                advertencias.append(f"⚠️ Línea o trazo muy fino detectado: {round(w, 2)} x {round(h, 2)} pt.")

    # Rasterizado y análisis de imagen
    imagenes = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)
    if imagenes:
        imagen = imagenes[0].convert("RGB")
        img_np = np.array(imagen)
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        # Calcular contraste como diferencia entre percentiles
        p2, p98 = np.percentile(img_gray, (2, 98))
        contraste = p98 - p2

        if contraste < 30:
            advertencias.append("⚠️ Imagen con bajo contraste. Podría afectar la calidad de impresión.")

    if not advertencias:
        advertencias.append("✅ El diseño parece apto para impresión flexográfica con los parámetros ingresados.")

    resumen = f"""
📐 Tamaño del diseño: {ancho_mm} x {alto_mm} mm
🧱 Paso del cilindro: {paso_mm} mm
🟡 Anilox: {anilox_lpi} lpi
------------------------------
""" + "\n".join(advertencias)

    return resumen
