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
        advertencias.append(
            f"<span class='icono error'>❌</span> El alto del diseño (<b>{alto_mm} mm</b>) es mayor al paso del cilindro (<b>{paso_mm} mm</b>)."
        )

    for bloque in contenido.get("blocks", []):
        if "lines" in bloque:
            for l in bloque["lines"]:
                for s in l["spans"]:
                    size = s.get("size", 0)
                    if size < 4:
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Texto pequeño detectado: '<b>{s['text']}</b>' ({round(size, 1)} pt). Riesgo de pérdida en impresión."
                        )
        elif "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            w = x1 - x0
            h = y1 - y0
            if w < 1 or h < 1:
                advertencias.append(
                    f"<span class='icono warn'>⚠️</span> Línea o trazo muy fino detectado: <b>{round(w, 2)} x {round(h, 2)} pt</b>."
                )

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
            advertencias.append(
                f"<span class='icono warn'>⚠️</span> Imagen con bajo contraste (<b>{contraste}</b>). Podría afectar la calidad de impresión."
            )

    if not advertencias:
        advertencias.append(
            "<span class='icono ok'>✔️</span> El diseño parece apto para impresión flexográfica con los parámetros ingresados."
        )

    resumen = f"""
<div>
  <p><b>📐 Tamaño del diseño:</b> {ancho_mm} x {alto_mm} mm</p>
  <p><b>🧱 Paso del cilindro:</b> {paso_mm} mm</p>
  <p><b>🟡 Anilox:</b> {anilox_lpi} lpi</p>
  <hr>
  {"<br>".join(advertencias)}
</div>
"""

    return resumen
