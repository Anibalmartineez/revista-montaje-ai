import fitz  # PyMuPDF
import os
import numpy as np
from pdf2image import convert_from_path
import cv2
from PyPDF2 import PdfReader
from PyPDF2.generic import IndirectObject
from PIL import Image, ImageOps
import re
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from html import unescape
from openai import OpenAI
import math

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def calcular_cobertura_total(pdf_path):
    """Calcula la cobertura total estimada del diseño como porcentaje de píxeles con tinta."""
    try:
        images = convert_from_path(pdf_path, dpi=300)
        total_pixels = 0
        ink_pixels = 0

        for img in images:
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
            ink_pixels += cv2.countNonZero(thresh)
            total_pixels += thresh.shape[0] * thresh.shape[1]

        if total_pixels == 0:
            return 0.0

        cobertura = (ink_pixels / total_pixels) * 100
        return round(cobertura, 2)

    except Exception as e:
        print(f"Error al calcular cobertura: {e}")
        return 0.0


def calcular_etiquetas_por_fila(
    ancho_bobina: float,
    ancho_etiqueta: float,
    separacion_horizontal: float = 0,
    margen_lateral: float = 0,
) -> int:
    """Calcula el número de etiquetas que caben horizontalmente en la bobina.

    La fórmula considera el ancho utilizable de la bobina restando los márgenes
    laterales y aplica la separación horizontal entre etiquetas. Se usa
    ``math.floor`` para asegurar que el resultado sea siempre un número entero
    correcto, incluso con valores decimales.

    Formula:
    ``floor((ancho_bobina - (2 * margen_lateral) + separacion_horizontal) /
    (ancho_etiqueta + separacion_horizontal))``
    """

    ancho_disponible = ancho_bobina - (2 * margen_lateral)
    if ancho_disponible <= 0 or (ancho_etiqueta + separacion_horizontal) <= 0:
        return 0

    return math.floor(
        (ancho_disponible + separacion_horizontal)
        / (ancho_etiqueta + separacion_horizontal)
    )


def corregir_sangrado_y_marcas(pdf_path: str) -> str:
    """Verifica sangrado y marcas de corte. Si faltan, genera un PDF corregido.

    Se analiza la primera página para comprobar si el contenido llega al borde
    (sangrado ≥ 3 mm) y si existen marcas de corte. Cuando falta alguno de los
    dos, se crea una nueva página expandida 3 mm por lado, se replica un borde
    espejado y se añaden marcas de corte profesionales. Devuelve la ruta del
    PDF (corregido o original).
    """

    doc = fitz.open(pdf_path)
    page = doc[0]

    page_rect = page.rect
    text_info = page.get_text("dict")
    x0, y0 = page_rect.x1, page_rect.y1
    x1, y1 = page_rect.x0, page_rect.y0
    for block in text_info.get("blocks", []):
        bx0, by0, bx1, by1 = block.get("bbox", (0, 0, 0, 0))
        x0, y0 = min(x0, bx0), min(y0, by0)
        x1, y1 = max(x1, bx1), max(y1, by1)
    content_rect = fitz.Rect(x0, y0, x1, y1)

    bleed_pts = 3 * 72 / 25.4
    margins = [
        content_rect.x0 - page_rect.x0,
        page_rect.x1 - content_rect.x1,
        content_rect.y0 - page_rect.y0,
        page_rect.y1 - content_rect.y1,
    ]
    has_bleed = all(m <= bleed_pts for m in margins)

    has_marks = False
    try:
        for d in page.get_drawings():
            for item in d.get("items", []):
                if item[0] == "l":  # línea
                    p0, p1 = item[1], item[2]
                    if (
                        p0.x < content_rect.x0
                        or p0.x > content_rect.x1
                        or p0.y < content_rect.y0
                        or p0.y > content_rect.y1
                        or p1.x < content_rect.x0
                        or p1.x > content_rect.x1
                        or p1.y < content_rect.y0
                        or p1.y > content_rect.y1
                    ):
                        has_marks = True
                        break
            if has_marks:
                break
    except Exception:
        has_marks = False

    if has_bleed and has_marks:
        doc.close()
        return pdf_path

    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    bleed_px = int(round(3 / 25.4 * 300))

    new_doc = fitz.open()
    if not has_bleed:
        new_width = page_rect.width + 2 * bleed_pts
        new_height = page_rect.height + 2 * bleed_pts
    else:
        new_width = page_rect.width
        new_height = page_rect.height
    new_page = new_doc.new_page(width=new_width, height=new_height)

    if not has_bleed:
        # Espejar bordes sin deformar contenido
        slice_img = ImageOps.mirror(img.crop((0, 0, bleed_px, img.height)))
        buf = BytesIO()
        slice_img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        rect = fitz.Rect(0, bleed_pts, bleed_pts, bleed_pts + page_rect.height)
        new_page.insert_image(rect, stream=buf.getvalue())
        buf.close()

        slice_img = ImageOps.mirror(
            img.crop((img.width - bleed_px, 0, img.width, img.height))
        )
        buf = BytesIO()
        slice_img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        rect = fitz.Rect(
            bleed_pts + page_rect.width,
            bleed_pts,
            2 * bleed_pts + page_rect.width,
            bleed_pts + page_rect.height,
        )
        new_page.insert_image(rect, stream=buf.getvalue())
        buf.close()

        slice_img = ImageOps.flip(img.crop((0, 0, img.width, bleed_px)))
        buf = BytesIO()
        slice_img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        rect = fitz.Rect(bleed_pts, 0, bleed_pts + page_rect.width, bleed_pts)
        new_page.insert_image(rect, stream=buf.getvalue())
        buf.close()

        slice_img = ImageOps.flip(
            img.crop((0, img.height - bleed_px, img.width, img.height))
        )
        buf = BytesIO()
        slice_img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        rect = fitz.Rect(
            bleed_pts,
            bleed_pts + page_rect.height,
            bleed_pts + page_rect.width,
            2 * bleed_pts + page_rect.height,
        )
        new_page.insert_image(rect, stream=buf.getvalue())
        buf.close()

        corners = [
            (
                ImageOps.flip(ImageOps.mirror(img.crop((0, 0, bleed_px, bleed_px)))),
                fitz.Rect(0, 0, bleed_pts, bleed_pts),
            ),
            (
                ImageOps.flip(
                    ImageOps.mirror(
                        img.crop((img.width - bleed_px, 0, img.width, bleed_px))
                    )
                ),
                fitz.Rect(
                    bleed_pts + page_rect.width,
                    0,
                    2 * bleed_pts + page_rect.width,
                    bleed_pts,
                ),
            ),
            (
                ImageOps.flip(
                    ImageOps.mirror(
                        img.crop((0, img.height - bleed_px, bleed_px, img.height))
                    )
                ),
                fitz.Rect(
                    0,
                    bleed_pts + page_rect.height,
                    bleed_pts,
                    2 * bleed_pts + page_rect.height,
                ),
            ),
            (
                ImageOps.flip(
                    ImageOps.mirror(
                        img.crop(
                            (
                                img.width - bleed_px,
                                img.height - bleed_px,
                                img.width,
                                img.height,
                            )
                        )
                    )
                ),
                fitz.Rect(
                    bleed_pts + page_rect.width,
                    bleed_pts + page_rect.height,
                    2 * bleed_pts + page_rect.width,
                    2 * bleed_pts + page_rect.height,
                ),
            ),
        ]
        for corner_img, rect in corners:
            buf = BytesIO()
            corner_img.save(buf, format="PNG", dpi=(300, 300))
            buf.seek(0)
            new_page.insert_image(rect, stream=buf.getvalue())
            buf.close()

    if not has_bleed:
        target_rect = fitz.Rect(
            bleed_pts, bleed_pts, bleed_pts + page_rect.width, bleed_pts + page_rect.height
        )
    else:
        target_rect = fitz.Rect(0, 0, page_rect.width, page_rect.height)
    new_page.show_pdf_page(target_rect, doc, page.number)

    if not has_marks:
        mark_len = 3 * 72 / 25.4
        width = 0.25
        if not has_bleed:
            x_left = bleed_pts
            x_right = bleed_pts + page_rect.width
            y_top = bleed_pts
            y_bottom = bleed_pts + page_rect.height
        else:
            x_left = bleed_pts
            x_right = page_rect.width - bleed_pts
            y_top = bleed_pts
            y_bottom = page_rect.height - bleed_pts
        color = (0, 0, 0)
        new_page.draw_line((x_left, y_top - mark_len), (x_left, y_top), color=color, width=width)
        new_page.draw_line((x_left - mark_len, y_top), (x_left, y_top), color=color, width=width)
        new_page.draw_line((x_right, y_top - mark_len), (x_right, y_top), color=color, width=width)
        new_page.draw_line((x_right + mark_len, y_top), (x_right, y_top), color=color, width=width)
        new_page.draw_line((x_left, y_bottom), (x_left, y_bottom + mark_len), color=color, width=width)
        new_page.draw_line((x_left - mark_len, y_bottom), (x_left, y_bottom), color=color, width=width)
        new_page.draw_line((x_right, y_bottom), (x_right, y_bottom + mark_len), color=color, width=width)
        new_page.draw_line((x_right + mark_len, y_bottom), (x_right, y_bottom), color=color, width=width)

    corrected_path = os.path.join(os.path.dirname(pdf_path), "archivo_corregido.pdf")
    new_doc.save(corrected_path)
    new_doc.close()
    doc.close()
    return corrected_path


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

def detectar_tramas_débiles(path_pdf):
    advertencias = []
    try:
        imagen = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)[0].convert("CMYK")
        img_np = np.array(imagen)

        umbral_trama = 13  # Aproximadamente 5% de 255
        min_pixeles_relevantes = 0.02  # 2% del total

        canales = ["Cian", "Magenta", "Amarillo", "Negro"]
        h, w, _ = img_np.shape
        total_pixeles = h * w

        for i, nombre in enumerate(canales):
            canal = img_np[:, :, i]
            pixeles_debiles = np.sum(canal < umbral_trama)
            proporcion = pixeles_debiles / total_pixeles
            if proporcion > min_pixeles_relevantes:
                advertencias.append(
                    f"<span class='icono warn'>⚠️</span> Trama muy débil detectada en <b>{nombre}</b>: {round(proporcion * 100, 2)}% del área está por debajo del 5%. Riesgo de pérdida en impresión."
                )

        if not advertencias:
            advertencias.append("<span class='icono ok'>✔️</span> No se detectaron tramas débiles en la imagen.")
    except Exception as e:
        advertencias.append(f"<span class='icono warn'>⚠️</span> No se pudo verificar la trama débil: {str(e)}")

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

def detectar_pantones_completamente(path_pdf):
    pantones = set()
    try:
        reader = PdfReader(path_pdf)
        for page in reader.pages:
            resources = page.get("/Resources")
            if isinstance(resources, IndirectObject):
                resources = resources.get_object()

            if resources and "/ColorSpace" in resources:
                colorspaces = resources.get("/ColorSpace")
                if isinstance(colorspaces, IndirectObject):
                    colorspaces = colorspaces.get_object()
                if isinstance(colorspaces, dict):
                    for name, cs in colorspaces.items():
                        cs_str = str(cs)
                        if "Separation" in cs_str or "PANTONE" in cs_str.upper():
                            pantones.add(name)
    except Exception as e:
        pantones.add(f"Error: {str(e)}")
    return pantones


def _normalizar_nombre_tinta(nombre):
    """Convierte nombres PDF como '/PANTONE#20394#20C' a 'PANTONE 294 C'."""
    if nombre.startswith("/"):
        nombre = nombre[1:]

    def reemplazo(match):
        return bytes.fromhex(match.group(1)).decode("latin-1")

    nombre = re.sub(r"#([0-9A-Fa-f]{2})", reemplazo, nombre)
    nombre = nombre.strip().upper()
    nombre = re.sub(r"(\d+)([A-Z])$", r"\1 \2", nombre)
    return nombre


def detectar_tintas_pantone(doc):
    """Devuelve una lista de nombres de tintas planas (Pantone/Spot) detectadas."""
    tintas = set()
    try:
        for page in doc.pages:
            resources = page.get("/Resources")
            if isinstance(resources, IndirectObject):
                resources = resources.get_object()
            if not isinstance(resources, dict):
                continue
            colorspaces = resources.get("/ColorSpace")
            if isinstance(colorspaces, IndirectObject):
                colorspaces = colorspaces.get_object()
            if not isinstance(colorspaces, dict):
                continue
            for _, cs in colorspaces.items():
                if isinstance(cs, IndirectObject):
                    cs = cs.get_object()
                if isinstance(cs, list) and len(cs) > 1 and cs[0] == "/Separation":
                    nombre = str(cs[1])
                    nombre_norm = _normalizar_nombre_tinta(nombre)
                    if re.search(r"(PANTONE|SPOT)", nombre_norm, re.IGNORECASE):
                        tintas.add(nombre_norm)
                else:
                    nombre = str(cs)
                    nombre_norm = _normalizar_nombre_tinta(nombre)
                    if re.search(r"(PANTONE|SPOT)", nombre_norm, re.IGNORECASE):
                        tintas.add(nombre_norm)
    except Exception:
        pass
    return sorted(tintas)


def _contar_overprints_pagina(doc, page):
    """Cuenta cuántas veces se aplica un estado gráfico con overprint en una página."""
    conteo = 0
    try:
        page_dict = doc.xref_object(page.xref)
        ext_match = re.search(r"/ExtGState\s*<<(.+?)>>", page_dict, re.S)
        if not ext_match:
            return 0
        overprint_names = []
        ext_content = ext_match.group(1)
        for name, xref in re.findall(r"/(\w+)\s+(\d+)\s+0\s+R", ext_content):
            obj = doc.xref_object(int(xref))
            if re.search(r"/(OP|op)\s+true", obj):
                overprint_names.append(name)
        if not overprint_names:
            return 0
        content = page.read_contents() or b""
        content_str = content.decode("latin-1", errors="ignore")
        for name in overprint_names:
            pattern = r"/" + re.escape(name) + r"\s+gs"
            conteo += len(re.findall(pattern, content_str))
    except Exception:
        return 0
    return conteo


def detectar_overprints(path_pdf):
    """Retorna el número total de objetos con overprint en el documento."""
    total = 0
    try:
        with fitz.open(path_pdf) as doc:
            for page in doc:
                total += _contar_overprints_pagina(doc, page)
    except Exception:
        return 0
    return total


def revisar_sangrado(pagina):
    sangrado_esperado = 3  # mm
    advertencias = []
    media = pagina.rect
    contenido = pagina.get_text("dict")
    elementos_cercanos = False
    for bloque in contenido.get("blocks", []):
        if "bbox" in bloque:
            x0, y0, x1, y1 = bloque["bbox"]
            margen_izq = convertir_pts_a_mm(x0)
            margen_der = convertir_pts_a_mm(media.width - x1)
            margen_sup = convertir_pts_a_mm(y0)
            margen_inf = convertir_pts_a_mm(media.height - y1)
            if min(margen_izq, margen_der, margen_sup, margen_inf) < sangrado_esperado:
                elementos_cercanos = True
                advertencias.append(
                    "<span class='icono warn'>⚠️</span> Elementos del diseño muy cercanos al borde. Verificar sangrado mínimo de 3 mm."
                )
                break
    if not elementos_cercanos:
        advertencias.append("<span class='icono ok'>✔️</span> Margen de seguridad adecuado respecto al sangrado.")
    return advertencias

def calcular_repeticiones_bobina(alto_diseño_mm, paso_cilindro_mm):
    """
    Calcula cuántas veces entra el diseño en el paso del cilindro flexográfico.
    Retorna el número de repeticiones y el espacio sobrante.
    """
    if alto_diseño_mm <= 0:
        return 0, paso_cilindro_mm
    repeticiones = int(paso_cilindro_mm // alto_diseño_mm)
    sobrante = round(paso_cilindro_mm - (repeticiones * alto_diseño_mm), 2)
    return repeticiones, sobrante


def generar_grafico_tinta(volumen_calculado, volumen_ideal, material):
    etiquetas = ["Calculado", "Ideal"]
    valores = [volumen_calculado, volumen_ideal]
    colores = ["#0056b3", "#999999"]

    plt.figure(figsize=(4, 3))
    barras = plt.bar(etiquetas, valores, color=colores)
    for barra, valor in zip(barras, valores):
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height(),
            f"{valor} ml/min",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    plt.ylabel("ml/min")
    plt.title(f"Transmisión de tinta ({material})")
    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    return imagen_base64

def revisar_diseño_flexo(
    path_pdf,
    anilox_lpi,
    paso_mm,
    material="",
    anilox_bcm=None,
    velocidad_impresion=None,
    cobertura_estimada=None,
):
    doc = fitz.open(path_pdf)
    pagina = doc[0]
    contenido = pagina.get_text("dict")
    ancho_mm, alto_mm = obtener_info_basica(pagina)
    advertencias = []
    cobertura_total = calcular_cobertura_total(path_pdf)
    advertencias.append(
        f"<span class='icono ink'>🖨️</span> Cobertura total estimada del diseño: <b>{cobertura_total}%</b>"
    )
    if cobertura_total > 85:
        advertencias.append(
            "<span class='icono warn'>⚠️</span> Cobertura muy alta. Riesgo de sobrecarga de tinta."
        )
    elif cobertura_total < 10:
        advertencias.append(
            "<span class='icono warn'>⚠️</span> Cobertura muy baja. Posible subcarga o diseño incompleto."
        )
    repeticiones, sobrante = calcular_repeticiones_bobina(alto_mm, paso_mm)
    advertencias.append(
        f"<span class='icono info'>🔁</span> El diseño entra <b>{repeticiones}</b> veces en el paso del cilindro de <b>{paso_mm} mm</b>. Sobrante: <b>{sobrante} mm</b>."
    )



    dim_adv = verificar_dimensiones(ancho_mm, alto_mm, paso_mm)
    textos_adv = verificar_textos_pequenos(contenido)
    lineas_adv = verificar_lineas_finas(contenido)
    contraste_adv = analizar_contraste(path_pdf)
    tramas_adv = detectar_tramas_débiles(path_pdf)
    modo_color_adv = verificar_modo_color(path_pdf)
    sangrado_adv = revisar_sangrado(pagina)

    advertencias += dim_adv
    advertencias += textos_adv
    advertencias += lineas_adv
    advertencias += contraste_adv
    advertencias += tramas_adv
    advertencias += modo_color_adv
    advertencias += sangrado_adv

    textos_pequenos_flag = any("Texto pequeño" in a and "warn" in a for a in textos_adv)
    lineas_finas_flag = any("Línea o trazo muy fino" in a and "warn" in a for a in lineas_adv)
    tramas_debiles_flag = any("Trama muy débil" in a and "warn" in a for a in tramas_adv)

    # Cobertura de tinta CMYK
    cobertura = {}
    try:
        img = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)[0].convert("CMYK")
        img_np = np.array(img)
        canales = ["Cian", "Magenta", "Amarillo", "Negro"]
        for i, nombre in enumerate(canales):
            canal = img_np[:, :, i]
            porcentaje = round(np.mean(canal / 255) * 100, 2)
            cobertura[nombre] = porcentaje
            advertencias.append(
                f"<span class='icono ink'>🖨️</span> Porcentaje estimado de cobertura de <b>{nombre}</b>: <b>{porcentaje}%</b>"
            )
    except Exception as e:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> No se pudo estimar la cobertura de tinta: {str(e)}"
        )

    # Detección de tintas planas (Pantone/Spot)
    try:
        reader_spot = PdfReader(path_pdf)
        tintas_planas = detectar_tintas_pantone(reader_spot)
        if tintas_planas:
            advertencias.append(
                f"<span class='icono warn'>🎨</span> Tintas planas detectadas: <b>{', '.join(tintas_planas)}</b>"
            )
        else:
            advertencias.append(
                "<span class='icono error'>❌</span> No se detectaron tintas planas (Pantone)"
            )
    except Exception as e:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> Error al verificar tintas planas: {str(e)}"
        )

    overprint_count = detectar_overprints(path_pdf)
    if overprint_count:
        advertencias.append(
            f"<span class='icono warn'>⚠️</span> Se detectaron <b>{overprint_count}</b> objetos con overprint habilitado. Posibles sobreimpresiones no intencionadas."
        )

    if not advertencias:
        advertencias.append(
            "<span class='icono ok'>✔️</span> El diseño parece apto para impresión flexográfica con los parámetros ingresados."
        )

    diagnostico_material = []
    material_norm = material.lower().strip()
    if material_norm == "film":
        negro = cobertura.get("Negro", 0)
        if negro > 50:
            diagnostico_material.append(
                f"<span class='icono warn'>⚠️</span> Cobertura alta de negro (<b>{negro}%</b>). Puede generar problemas de adherencia o secado en film."
            )
        else:
            diagnostico_material.append("<span class='icono ok'>✔️</span> Cobertura de negro adecuada para impresión en film.")
        if tramas_debiles_flag:
            diagnostico_material.append("<span class='icono warn'>⚠️</span> Las tramas débiles podrían no transferirse correctamente sobre film.")
    elif material_norm == "papel":
        if textos_pequenos_flag or lineas_finas_flag:
            diagnostico_material.append("<span class='icono warn'>⚠️</span> En papel, la ganancia de punto puede afectar textos pequeños y líneas finas.")
        else:
            diagnostico_material.append("<span class='icono ok'>✔️</span> No se detectaron elementos sensibles a la ganancia de punto en papel.")
    elif material_norm == "etiqueta adhesiva":
        total_cobertura = sum(cobertura.values())
        if total_cobertura > 240:
            diagnostico_material.append(
                f"<span class='icono warn'>⚠️</span> Cobertura total alta (<b>{round(total_cobertura,2)}%</b>). Puede ocasionar problemas de secado en etiquetas adhesivas."
            )
        else:
            diagnostico_material.append("<span class='icono ok'>✔️</span> Cobertura total adecuada para etiqueta adhesiva.")
    elif material_norm:
        diagnostico_material.append(
            f"<span class='icono info'>ℹ️</span> Material '<b>{material}</b>' no reconocido. Sin recomendaciones específicas."
        )

    seccion_material = ""
    if diagnostico_material:
        seccion_material = "<hr><p><b>Diagnóstico según material de impresión:</b></p><p>" + "<br>".join(diagnostico_material) + "</p>"

    seccion_tinta = ""
    imagen_tinta = ""
    if (
        anilox_bcm is not None
        and velocidad_impresion is not None
    ):
        try:
            if cobertura_estimada is None:
                cobertura_estimada = cobertura_total
            factores = {"film": 0.7, "papel": 1.0, "etiqueta adhesiva": 0.85}
            factor_material = factores.get(material_norm, 1.0)
            cobertura_frac = float(cobertura_estimada) / 100.0
            tinta_ml = anilox_bcm * cobertura_frac * velocidad_impresion * factor_material
            tinta_ml = round(tinta_ml, 2)
            umbral_bajo = 50
            umbral_alto = 200
            if tinta_ml < umbral_bajo:
                advertencia_tinta = (
                    "Riesgo de subcarga de tinta, posible pérdida de densidad o colores pálidos."
                )
            elif tinta_ml > umbral_alto:
                advertencia_tinta = (
                    "Riesgo de sobrecarga de tinta, puede generar ganancia de punto o tiempos de secado muy elevados."
                )
            else:
                advertencia_tinta = "Transmisión de tinta estimada en rango seguro."

            porcentaje_barra = min(tinta_ml / umbral_alto * 100, 100)
            barra_html = (
                "<div style='background:#ddd;border-radius:4px;width:100%;height:10px;'>"
                f"<div style='background:#0056b3;width:{porcentaje_barra}%;height:100%;'></div></div>"
            )

            valores_ideales = {"film": 120, "papel": 180, "etiqueta adhesiva": 150}
            tinta_ideal = valores_ideales.get(material_norm, 150)
            imagen_tinta = generar_grafico_tinta(tinta_ml, tinta_ideal, material)

            seccion_tinta = (
                "<hr><p><b>🖌️ Simulación de transmisión de tinta</b></p>"
                f"<p>Cantidad estimada de tinta transferida: <b>{tinta_ml} ml/min</b></p>"
                f"{barra_html}"
                f"<p>{advertencia_tinta}</p>"
            )
        except Exception as e:
            seccion_tinta = (
                "<hr><p><b>🖌️ Simulación de transmisión de tinta</b></p>"
                f"<p>Error en la simulación: {str(e)}</p>"
            )

    resumen = f"""
<div>
  <p><b>📐 Tamaño del diseño:</b> {ancho_mm} x {alto_mm} mm</p>
  <p><b>🧱 Paso del cilindro:</b> {paso_mm} mm</p>
  <p><b>🟡 Anilox:</b> {anilox_lpi} lpi</p>
  <hr>
  {'<br>'.join(advertencias)}
  {seccion_material}
  {seccion_tinta}
</div>
"""
    diagnostico_texto = generar_diagnostico_texto(resumen)
    return resumen, imagen_tinta, diagnostico_texto


def generar_diagnostico_texto(html_diagnostico: str) -> str:
    """Convierte el diagnóstico en HTML a un texto plano legible."""
    texto = re.sub(r"<[^>]+>", "", html_diagnostico)
    texto = unescape(texto)
    lineas = [line.strip() for line in texto.splitlines() if line.strip()]
    return "\n".join(lineas)


def generar_sugerencia_produccion(diagnostico_texto: str, resultado_revision: str) -> str:
    """Genera sugerencias prácticas de producción basadas en el diagnóstico."""
    try:
        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un especialista en producción de impresión flexográfica. "
                    "Brinda recomendaciones prácticas basadas en el diagnóstico entregado. "
                    "Evalúa si el archivo está listo para impresión, riesgos en máquina, tipo de anilox según cobertura, "
                    "cambios de técnica de impresión, uso de barniz, doble pasada o reducción de colores y ajustes de preprensa."
                ),
            },
            {
                "role": "user",
                "content": f"Diagnóstico:\n{diagnostico_texto}\n\nResultado de la revisión:\n{resultado_revision}",
            },
        ]
        respuesta = client.chat.completions.create(
            model="gpt-4",
            messages=mensajes,
            temperature=0.3,
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al obtener sugerencia de producción: {str(e)}"
