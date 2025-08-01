import tempfile
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
import os

def generar_montaje(path_pdf_etiqueta, ancho, alto, separacion, bobina, cantidad):
    etiquetas_x = bobina // (ancho + separacion)
    etiquetas_y = 2  # Fijo por ahora

    etiquetas_por_repeticion = etiquetas_x * etiquetas_y
    if etiquetas_por_repeticion == 0:
        raise ValueError("El ancho de bobina es muy pequeño para colocar al menos una etiqueta con la separación dada.")

    repeticiones = (cantidad + etiquetas_por_repeticion - 1) // etiquetas_por_repeticion

    # Abrir el PDF de la etiqueta
    doc_origen = fitz.open(path_pdf_etiqueta)
    if len(doc_origen) == 0:
        raise ValueError("El archivo PDF está vacío o es inválido.")
    
    pagina_etiqueta = doc_origen[0]
    output = fitz.open()

    # Altura dinámica basada en cantidad de filas
    altura_pagina_mm = etiquetas_y * (alto + separacion)

    for r in range(repeticiones):
        nueva_pagina = output.new_page(
            width=bobina * mm,
            height=altura_pagina_mm * mm
        )
        for i in range(etiquetas_x):
            for j in range(etiquetas_y):
                x = i * (ancho + separacion) * mm
                y = j * (alto + separacion) * mm
                rect = fitz.Rect(x, y, x + ancho * mm, y + alto * mm)
                nueva_pagina.show_pdf_page(rect, doc_origen, 0)

    nombre_archivo = f"montaje_flexo_{os.path.basename(path_pdf_etiqueta)}"
    ruta_salida = os.path.join("output_flexo", nombre_archivo)

    output.save(ruta_salida)
    output.close()
    doc_origen.close()

    return ruta_salida

def revisar_diseño_flexo(path_pdf, anilox_lpi, paso_mm):
    import fitz

    doc = fitz.open(path_pdf)
    pagina = doc[0]
    media = pagina.rect
    contenido = pagina.get_text("dict")
    advertencias = []

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

    if not advertencias:
        advertencias.append("✅ El diseño parece apto para impresión flexográfica con los parámetros ingresados.")

    resumen = f"""
📐 Tamaño del diseño: {ancho_mm} x {alto_mm} mm
🧱 Paso del cilindro: {paso_mm} mm
🟡 Anilox: {anilox_lpi} lpi
------------------------------
""" + "\n".join(advertencias)

    return resumen
