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
