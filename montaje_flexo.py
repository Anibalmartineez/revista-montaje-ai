import fitz  # PyMuPDF
import os
import numpy as np
from pdf2image import convert_from_path
import cv2
from PyPDF2 import PdfReader
from PyPDF2.generic import IndirectObject
from collections import Counter
import re
from PIL import Image


def convertir_pts_a_mm(valor_pts):
    return round(valor_pts * 25.4 / 72, 2)


def obtener_info_basica(pagina):
    media = pagina.rect
    ancho_mm = convertir_pts_a_mm(media.width)
    alto_mm = convertir_pts_a_mm(media.height)
    return ancho_mm, alto_mm


def verificar_dimensiones(ancho_mm, alto_mm, paso_mm):
    advertencias = []
    if alto_mm > paso_mm:
        advertencias.append(
            f"<span class='icono error'>❌</span> El alto del diseño (<b>{alto_mm} mm</b>) es mayor al paso del cilindro (<b>{paso_mm} mm</b>)."
        )
    return advertencias


def verificar_textos_pequenos(contenido):
    advertencias = []
    for bloque in contenido.get("blocks", []):
        if "lines" in bloque:
            for l in bloque["lines"]:
                for s in l["spans"]:
                    size = s.get("size", 0)
                    if size < 4:
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Texto pequeño detectado: '<b>{s['text']}</b>' ({round(size, 1)} pt). Riesgo de pérdida en impresión."
                        )
    return advertencias


def verificar_lineas_finas(contenido):
    advertencias = []
    for bloque in contenido.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            w = x1 - x0
            h = y1 - y0
            if w < 1 or h < 1:
                advertencias.append(
                    f"<span class='icono warn'>⚠️</span> Línea o trazo muy fino detectado: <b>{round(w, 2)} x {round(h, 2)} pt</b>."
                )
    return advertencias


def analizar_contraste(path_pdf):
    advertencias = []
    imagenes = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)
    if imagenes:
        imagen = imagenes[0].convert("RGB")
        img_np = np.array(imagen)
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        p2, p98 = np.percentile(img_gray, (2, 98))
        contraste = p98 - p2
        if contraste < 30:
            advertencias.append(
                f"<span class='icono warn'>⚠️</span> Imagen con bajo contraste (<b>{contraste}</b>). Podría afectar la calidad de impresión."
            )
    return advertencias


def verificar_modo_color(path_pdf):
    advertencias = []
    try:
        reader = PdfReader(path_pdf)
        for page_num, page in enumerate(reader.pages):
            resources = page.get("/Resources")
            if not resources:
                continue

            xobject = resources.get("/XObject")
            if isinstance(xobject, IndirectObject):
                xobject = xobject.get_object()

            if not isinstance(xobject, dict):
                continue

            for obj_name, obj_ref in xobject.items():
                obj = obj_ref.get_object()
                if obj.get("/Subtype") == "/Image":
                    color_space = obj.get("/ColorSpace")

                    if isinstance(color_space, IndirectObject):
                        color_space = color_space.get_object()

                    if isinstance(color_space, list):
                        color_model = color_space[0]
                    else:
                        color_model = color_space

                    if color_model == "/DeviceRGB":
                        advertencias.append(
                            f"<span class='icono error'>❌</span> Imagen en RGB detectada en la página {page_num+1}. Convertir a CMYK."
                        )
    except Exception as e:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> No se pudo verificar el modo de color: {str(e)}"
        )

    return advertencias


def revisar_sangrado(pagina):
    sangrado_esperado = 3  # mm
    advertencias = []
    media = pagina.rect
    contenido = pagina.get_text("dict")
    for bloque in contenido.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            margen_izq = convertir_pts_a_mm(x0)
            margen_der = convertir_pts_a_mm(media.width - x1)
            margen_sup = convertir_pts_a_mm(y0)
            margen_inf = convertir_pts_a_mm(media.height - y1)
            if min(margen_izq, margen_der, margen_sup, margen_inf) < sangrado_esperado:
                advertencias.append(
                    "<span class='icono warn'>⚠️</span> Elementos del diseño muy cercanos al borde. Verificar sangrado mínimo de 3 mm."
                )
                break
    return advertencias


def revisar_diseño_flexo(path_pdf, anilox_lpi, paso_mm):
    doc = fitz.open(path_pdf)
    pagina = doc[0]
    contenido = pagina.get_text("dict")
    
    ancho_mm, alto_mm = obtener_info_basica(pagina)

    advertencias = []
    advertencias += verificar_dimensiones(ancho_mm, alto_mm, paso_mm)
    advertencias += verificar_textos_pequenos(contenido)
    advertencias += verificar_lineas_finas(contenido)
    advertencias += analizar_contraste(path_pdf)
    advertencias += verificar_modo_color(path_pdf)
    advertencias += revisar_sangrado(pagina)

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
