import fitz  # PyMuPDF
import os
import numpy as np
from pdf2image import convert_from_path
import cv2
from PyPDF2 import PdfReader
from PyPDF2.generic import IndirectObject
from collections import Counter
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
    if ancho_mm > 330:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> El ancho del diseño (<b>{ancho_mm} mm</b>) podría exceder el ancho útil de la máquina. Verificar configuración."
        )
    return advertencias


def verificar_textos_pequenos(contenido):
    advertencias = []
    encontrados = False
    for bloque in contenido.get("blocks", []):
        if "lines" in bloque:
            for l in bloque["lines"]:
                for s in l["spans"]:
                    size = s.get("size", 0)
                    fuente = s.get("font", "")
                    if size < 4:
                        encontrados = True
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Texto pequeño detectado: '<b>{s['text']}</b>' ({round(size, 1)} pt, fuente: {fuente}). Riesgo de pérdida en impresión."
                        )
    if not encontrados:
        advertencias.append("<span class='icono ok'>✔️</span> No se encontraron textos menores a 4 pt.")
    return advertencias


def verificar_lineas_finas(contenido):
    advertencias = []
    encontrados = False
    for bloque in contenido.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            w = x1 - x0
            h = y1 - y0
            if (w < 0.3 or h < 0.3):
                encontrados = True
                advertencias.append(
                    f"<span class='icono warn'>⚠️</span> Línea o trazo muy fino detectado: <b>{round(w, 2)} x {round(h, 2)} pt</b>. Riesgo de pérdida."
                )
    if not encontrados:
        advertencias.append("<span class='icono ok'>✔️</span> No se detectaron líneas finas con riesgo de pérdida.")
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
        else:
            advertencias.append(f"<span class='icono ok'>✔️</span> Contraste adecuado: <b>{contraste}</b>.")
    else:
        advertencias.append("<span class='icono warn'>⚠️</span> No se pudo analizar el contraste.")
    return advertencias


def verificar_modo_color(path_pdf):
    advertencias = []
    encontrado = False
    try:
        reader = PdfReader(path_pdf)
        for page_num, page in enumerate(reader.pages):
            resources = page.get("/Resources")
            if isinstance(resources, IndirectObject):
                resources = resources.get_object()
            if not isinstance(resources, dict):
                continue
            xobjects = resources.get("/XObject")
            if isinstance(xobjects, IndirectObject):
                xobjects = xobjects.get_object()
            if not isinstance(xobjects, dict):
                continue
            for obj_name, obj_ref in xobjects.items():
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
                        encontrado = True
                        advertencias.append(
                            f"<span class='icono error'>❌</span> Imagen en RGB detectada en la página {page_num+1}. Convertir a CMYK."
                        )
                    elif color_model == "/DeviceGray":
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Imagen en escala de grises detectada en la página {page_num+1}. Verificar si es intencional."
                        )
        if not encontrado:
            advertencias.append("<span class='icono ok'>✔️</span> Todas las imágenes están en modo CMYK o escala de grises.")
    except Exception as e:
        advertencias.append(f"<span class='icono warn'>⚠️</span> No se pudo verificar el modo de color: {str(e)}")
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


def verificar_resolucion_imagenes(path_pdf):
    advertencias = []
    try:
        reader = PdfReader(path_pdf)
        for page_num, page in enumerate(reader.pages):
            resources = page.get("/Resources")
            if isinstance(resources, IndirectObject):
                resources = resources.get_object()
            if not isinstance(resources, dict):
                continue
            xobjects = resources.get("/XObject")
            if isinstance(xobjects, IndirectObject):
                xobjects = xobjects.get_object()
            if not isinstance(xobjects, dict):
                continue
            for obj_ref in xobjects.values():
                obj = obj_ref.get_object()
                if obj.get("/Subtype") == "/Image":
                    width = obj.get("/Width", 0)
                    height = obj.get("/Height", 0)
                    if width < 300 or height < 300:
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Imagen con resolución baja detectada ({width}x{height} px)."
                        )
    except Exception as e:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> Error verificando resolución de imágenes: {str(e)}"
        )
    return advertencias


def estimar_consumo_tinta(path_pdf):
    resumen_tintas = []
    try:
        imagen = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)[0]
        img_cmyk = imagen.convert("CMYK")
        canales = img_cmyk.split()
        nombres = ['Cian', 'Magenta', 'Amarillo', 'Negro']
        for i, canal in enumerate(canales):
            np_canal = np.array(canal)
            porcentaje = round(np.mean(np_canal) / 255 * 100, 2)
            resumen_tintas.append(
                f"<span class='icono tinta'>🖨️</span> Porcentaje estimado de cobertura de <b>{nombres[i]}</b>: <b>{100 - porcentaje:.2f}%</b>"
            )
    except Exception as e:
        resumen_tintas.append(
            f"<span class='icono warn'>⚠️</span> No se pudo estimar el consumo de tinta: {str(e)}"
        )
    return resumen_tintas


def revisar_diseño_flexo(path_pdf, anilox_lpi, paso_mm):
    doc = fitz.open(path_pdf)
    if len(doc) > 1:
        advertencia_paginas = ["<span class='icono warn'>⚠️</span> El archivo contiene más de una página. Solo se analiza la primera."]
    else:
        advertencia_paginas = []

    pagina = doc[0]
    contenido = pagina.get_text("dict")
    ancho_mm, alto_mm = obtener_info_basica(pagina)

    advertencias = []
    advertencias += advertencia_paginas
    advertencias += verificar_dimensiones(ancho_mm, alto_mm, paso_mm)
    advertencias += verificar_textos_pequenos(contenido)
    advertencias += verificar_lineas_finas(contenido)
    advertencias += analizar_contraste(path_pdf)
    advertencias += verificar_modo_color(path_pdf)
    advertencias += verificar_resolucion_imagenes(path_pdf)
    advertencias += revisar_sangrado(pagina)
    advertencias += estimar_consumo_tinta(path_pdf)

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
  {'<br>'.join(advertencias)}
</div>
"""

    return resumen
