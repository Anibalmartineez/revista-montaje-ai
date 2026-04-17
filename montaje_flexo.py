import fitz  # PyMuPDF
import os
import math
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
from typing import Any, Dict, List
from types import SimpleNamespace
from services.openai_client import create_chat_completion

from utils import (
    convertir_pts_a_mm,
    obtener_info_basica,
    verificar_dimensiones,
    normalizar_material,
)

from diagnostico_flexo import coeficiente_material, filtrar_objetos_sistema
from advertencias_disenio import analizar_advertencias_disenio
from cobertura_utils import calcular_metricas_cobertura
from reporte_tecnico import generar_reporte_tecnico, resumen_cobertura_tac
from flexo_config import get_flexo_thresholds
from tinta_utils import (
    InkParams,
    calcular_transmision_tinta,
    normalizar_coberturas,
    get_ink_ideal_mlmin,
    clasificar_riesgo_por_ideal,
)

# Inicializa el cliente de OpenAI solo si hay API key disponible, evitando
# errores durante la importación en entornos de test.
PT_PER_MM = 72 / 25.4


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
        for d in filtrar_objetos_sistema(page.get_drawings(), None):
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

def verificar_resolucion_imagenes(path_pdf):
    items = []
    try:
        with fitz.open(path_pdf) as doc:
            for p, page in enumerate(doc, start=1):
                for (xref, *_rest) in page.get_images(full=True):
                    try:
                        obj = doc.xref_object(xref) or ""
                    except Exception:
                        obj = ""
                    is_lineart = "BitsPerComponent 1" in obj
                    try:
                        pm = fitz.Pixmap(doc, xref)
                        wpx, hpx = pm.width, pm.height
                    except Exception:
                        try:
                            wpx, hpx = _rest[1], _rest[2]
                        except Exception:
                            wpx = hpx = 0
                    for rect in page.get_image_rects(xref):
                        dpi_x = wpx / (rect.width / 72.0) if rect.width else 0
                        dpi_y = hpx / (rect.height / 72.0) if rect.height else 0
                        dpi = int(min(dpi_x, dpi_y))
                        thr = 600 if is_lineart else 300
                        tipo = "line-art" if is_lineart else "foto"
                        if dpi < thr:
                            items.append(f"<li><span class='icono error'>❌</span> Imagen xref {xref} pág {p}: <b>{dpi} DPI</b> efectivos (mín {thr} para {tipo}).</li>")
        if not items:
            items.append("<li><span class='icono ok'>✔️</span> Resolución efectiva correcta en todas las imágenes.</li>")
    except Exception as e:
        items.append(f"<li><span class='icono warn'>⚠️</span> No se pudo verificar la resolución de imágenes: {e}</li>")
    return items


def detectar_capas_especiales(path_pdf):
    items = []
    try:
        reader = PdfReader(path_pdf)
        spots = set()
        patrones = {
            "white": re.compile(r"(white|blanco)", re.I),
            "varnish": re.compile(r"(varnish|barniz|uv)", re.I),
            "cut": re.compile(r"(cutcontour|cut|troquel|dieline)", re.I),
        }
        try:
            tintas_planas = detectar_tintas_pantone(reader)
            for t in tintas_planas:
                spots.add(str(t))
        except Exception:
            pass
        for page in reader.pages:
            res = page.get("/Resources")
            if isinstance(res, IndirectObject):
                res = res.get_object()
            if not isinstance(res, dict):
                continue
            cs = res.get("/ColorSpace")
            if isinstance(cs, IndirectObject):
                cs = cs.get_object()
            if isinstance(cs, dict):
                for _, v in cs.items():
                    if isinstance(v, IndirectObject):
                        v = v.get_object()
                    s = str(v)
                    if "/Separation" in s or "/DeviceN" in s:
                        spots.add(s)
        spots_str = " | ".join(sorted(spots)) if spots else ""
        if spots_str:
            items.append(f"<li><b>Spots detectados:</b> {spots_str}</li>")
        try:
            over = detectar_overprints(path_pdf)
        except Exception:
            over = 0
        if patrones["white"].search(spots_str or ""):
            icon = "ok" if over else "warn"
            items.append(f"<li><span class='icono {icon}'>{'✔️' if over else '⚠️'}</span> <b>White/Blanco</b> detectado. Usar <b>overprint</b> y orden correcto de impresión.</li>")
        if patrones["varnish"].search(spots_str or ""):
            items.append("<li>Detectado <b>Barniz/Varnish</b>. Confirmar cobertura y sobreimpresión.</li>")
        if patrones["cut"].search(spots_str or ""):
            items.append("<li>Detectado <b>CutContour/Troquel</b>. Mantener como spot, sin CMYK y en overprint.</li>")
        if not items:
            items.append("<li><span class='icono ok'>✔️</span> No se detectaron capas especiales.</li>")
    except Exception as e:
        items.append(f"<li><span class='icono warn'>⚠️</span> No se pudo analizar capas especiales: {e}</li>")
    return items


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
    mensajes: List[str] = []
    advertencias_overlay: List[Dict[str, Any]] = []
    hay_tramas = False

    bbox_total: List[float] | None = None
    try:
        with fitz.open(path_pdf) as doc_bbox:
            page0 = doc_bbox.load_page(0)
            rect = page0.rect
            bbox_total = [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]
    except Exception:
        bbox_total = None

    try:
        imagenes = convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1)
        if not imagenes:
            raise ValueError("No se pudieron rasterizar páginas del PDF")
        imagen = imagenes[0].convert("CMYK")
        img_np = np.array(imagen)

        umbral_trama = 13  # Aproximadamente 5% de 255
        min_pixeles_relevantes = 0.02  # 2% del total

        canales = ["Cian", "Magenta", "Amarillo", "Negro"]
        h, w, _ = img_np.shape
        total_pixeles = h * w if h and w else 1

        for i, nombre in enumerate(canales):
            canal = img_np[:, :, i]
            # Consideramos solo los píxeles con cobertura real (>0) por debajo del 5%
            mask = (canal > 0) & (canal < umbral_trama)
            pixeles_debiles = int(np.sum(mask))
            proporcion = pixeles_debiles / total_pixeles
            if proporcion > min_pixeles_relevantes:
                hay_tramas = True
                porcentaje = round(proporcion * 100, 2)
                mensaje = (
                    "<span class='icono warn'>⚠️</span> Trama muy débil detectada en "
                    f"<b>{nombre}</b>: {porcentaje}% del área está por debajo del 5%. Riesgo de pérdida en impresión."
                )
                mensajes.append(mensaje)
                bbox = bbox_total if bbox_total else [0.0, 0.0, 1.0, 1.0]
                advertencias_overlay.append(
                    {
                        "id": f"sistema_trama_debil_{nombre.lower()}",
                        "tipo": "trama_debil",
                        "bbox": bbox,
                        "nivel": "medio",
                        "descripcion": f"Trama débil en {nombre} ({porcentaje}% del área)",
                        "mensaje": f"Trama débil en {nombre}",
                        "pagina": 1,
                        "label": nombre,
                    }
                )

        if not mensajes:
            mensajes.append("<span class='icono ok'>✔️</span> No se detectaron tramas débiles en la imagen.")
    except Exception as e:
        mensajes.append(f"<span class='icono warn'>⚠️</span> No se pudo verificar la trama débil: {str(e)}")

    return {
        "mensajes": mensajes,
        "advertencias": advertencias_overlay,
        "hay_tramas_debiles": hay_tramas,
    }


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
    material_norm = normalizar_material(material)
    material_coef_val = coeficiente_material(material, default=1.0) or 1.0
    ancho_mm, alto_mm = obtener_info_basica(pagina)
    ancho_util_m = round((ancho_mm or 0.0) / 1000.0, 4) if ancho_mm else 0.0

    diseno_info = [
        f"<li><span class='icono design'>📐</span> Tamaño del diseño: <b>{ancho_mm} x {alto_mm} mm</b></li>",
        f"<li><span class='icono anilox'>🟡</span> Anilox: <b>{anilox_lpi} lpi</b></li>",
    ]
    montaje_info = [
        f"<li><span class='icono design'>🧱</span> Paso del cilindro: <b>{paso_mm} mm</b></li>",
    ]
    if anilox_bcm is not None:
        diseno_info.append(
            f"<li><span class='icono anilox'>🟤</span> BCM del anilox: <b>{anilox_bcm:.2f} cm³/m²</b></li>"
        )
    if velocidad_impresion is not None:
        montaje_info.append(
            f"<li><span class='icono info'>⚡</span> Velocidad estimada de impresión: <b>{velocidad_impresion:.2f} m/min</b></li>"
        )
    cobertura_info: List[str] = []
    cobertura_manual = None
    if cobertura_estimada is not None:
        try:
            cobertura_manual = float(cobertura_estimada)
        except (TypeError, ValueError):
            cobertura_manual = None
    riesgos_info: List[str] = []

    thresholds = get_flexo_thresholds(material_norm, anilox_lpi)
    metricas_cobertura: Dict[str, Any] | None = None
    cobertura_total: float | None = None
    tac_total: float | None = None
    cobertura_promedio: Dict[str, float] = {}
    cobertura_por_canal_letras: Dict[str, float] = {}
    metrics = SimpleNamespace(
        tac_total=None,
        tac_p95=None,
        tac_max=None,
        cobertura_por_canal=None,
        cobertura_total=None,
    )
    try:
        metricas_cobertura = calcular_metricas_cobertura(path_pdf, dpi=300)
        for clave in ("tac_p95", "tac_max"):
            valor = metricas_cobertura.get(clave)
            if valor is None:
                continue
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numero):
                continue
            setattr(metrics, clave, round(numero, 2))
        cobertura_promedio_raw = metricas_cobertura.get("cobertura_promedio")
        if isinstance(cobertura_promedio_raw, dict):
            for canal, valor in cobertura_promedio_raw.items():
                try:
                    porcentaje = float(valor)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(porcentaje):
                    continue
                porcentaje = round(porcentaje, 2)
                cobertura_promedio[canal] = porcentaje
            if cobertura_promedio:
                cobertura_por_canal_letras = normalizar_coberturas(cobertura_promedio)
                if cobertura_por_canal_letras:
                    metrics.cobertura_por_canal = dict(cobertura_por_canal_letras)

        cobertura_total_val = metricas_cobertura.get("cobertura_total")
        if cobertura_total_val is not None:
            try:
                cobertura_total = float(cobertura_total_val)
            except (TypeError, ValueError):
                cobertura_total = None
        if cobertura_total is not None and not math.isfinite(cobertura_total):
            cobertura_total = None

        if cobertura_total is not None:
            cobertura_total_redondeada = round(cobertura_total, 2)
            metrics.cobertura_total = cobertura_total_redondeada
            cobertura_info.append(
                "<li><span class='icono ink'>🖨️</span> Cobertura total estimada del diseño: "
                f"<b>{cobertura_total_redondeada}%</b></li>"
            )
            if cobertura_total_redondeada > 85:
                riesgos_info.append(
                    "<li><span class='icono warning'>⚠️</span> Cobertura muy alta. Riesgo de sobrecarga de tinta.</li>"
                )
            elif cobertura_total_redondeada < 10:
                riesgos_info.append(
                    "<li><span class='icono warning'>⚠️</span> Cobertura muy baja. Posible subcarga o diseño incompleto.</li>"
                )

        if cobertura_por_canal_letras:
            tac_total_calculado = sum(cobertura_por_canal_letras.values())
            if math.isfinite(tac_total_calculado):
                tac_total = round(float(tac_total_calculado), 2)
                metrics.tac_total = tac_total
                metricas_cobertura["tac_total"] = tac_total
                cobertura_info.append(
                    "<li><span class='icono ink'>🖨️</span> TAC promedio detectado (suma CMYK): "
                    f"<b>{round(tac_total, 2)}%</b></li>"
                )
    except Exception as e:
        cobertura_total = None
        tac_total = cobertura_manual
        metricas_cobertura = None
        cobertura_promedio = {}
        riesgos_info.append(
            f"<li><span class='icono warning'>⚠️</span> No se pudo estimar la cobertura de tinta: {e}</li>"
        )
    if metrics.tac_total is None and tac_total is not None:
        try:
            tac_total_float = float(tac_total)
        except (TypeError, ValueError):
            tac_total_float = None
        else:
            if math.isfinite(tac_total_float):
                metrics.tac_total = round(tac_total_float, 2)
    if metricas_cobertura is None and cobertura_manual is not None:
        cobertura_info.append(
            "<li><span class='icono ink'>🖨️</span> Cobertura ingresada para simulación: "
            f"<b>{cobertura_manual:.2f}%</b></li>"
        )

    repeticiones, sobrante = calcular_repeticiones_bobina(alto_mm, paso_mm)
    montaje_info.append(
        f"<li><span class='icono info'>🔁</span> El diseño entra <b>{repeticiones}</b> veces en el paso del cilindro de <b>{paso_mm} mm</b>. Sobrante: <b>{sobrante} mm</b>.</li>"
    )

    dim_adv = verificar_dimensiones(ancho_mm, alto_mm, paso_mm)
    adv_res = analizar_advertencias_disenio(path_pdf, material_norm, pagina=pagina, contenido=contenido)
    textos_adv = adv_res["textos"]
    lineas_adv = adv_res["lineas"]
    modo_color_adv = adv_res["modo_color"]
    sangrado_adv = adv_res["sangrado"]
    advertencias_overlay = adv_res["overlay"]
    resolucion_items = verificar_resolucion_imagenes(path_pdf)
    resolucion_minima = None
    for item in resolucion_items:
        m = re.search(r">\s*(\d+)\s*DPI", item)
        if m:
            dpi = int(m.group(1))
            resolucion_minima = dpi if resolucion_minima is None else min(resolucion_minima, dpi)
    if metricas_cobertura:
        til_items = resumen_cobertura_tac(metricas_cobertura, material_norm)
    else:
        til_items = ["<li><span class='icono warn'>⚠️</span> No se pudo estimar TAC/cobertura.</li>"]
    capas_items = detectar_capas_especiales(path_pdf)
    contraste_adv = analizar_contraste(path_pdf)
    tramas_adv = detectar_tramas_débiles(path_pdf)
    tramas_mensajes = tramas_adv.get("mensajes", [])
    tramas_overlay = tramas_adv.get("advertencias", [])

    if advertencias_overlay:
        advertencias_overlay.extend(tramas_overlay)
    else:
        advertencias_overlay = list(tramas_overlay)

    for lista in [dim_adv, textos_adv, contraste_adv, tramas_mensajes, modo_color_adv, sangrado_adv]:
        riesgos_info.extend([f"<li>{a}</li>" for a in lista])
    riesgos_info.extend(lineas_adv)

    textos_pequenos_flag = any("Texto pequeño" in a and "warn" in a for a in textos_adv)
    lineas_finas_flag = any("trazos" in a.lower() and "warn" in a for a in lineas_adv)
    tramas_debiles_flag = bool(tramas_adv.get("hay_tramas_debiles")) or any(
        "Trama muy débil" in a and "warn" in a for a in tramas_mensajes
    )

    if metrics.cobertura_por_canal:
        nombres_canal = {"C": "Cian", "M": "Magenta", "Y": "Amarillo", "K": "Negro"}
        for canal, porcentaje in metrics.cobertura_por_canal.items():
            nombre = nombres_canal.get(canal, canal)
            cobertura_info.append(
                "<li><span class='icono ink'>🖨️</span> Porcentaje estimado de cobertura de "
                f"<b>{nombre}</b>: <b>{porcentaje:.2f}%</b></li>"
            )

    # Detección de tintas planas (Pantone/Spot)
    try:
        reader_spot = PdfReader(path_pdf)
        tintas_planas = detectar_tintas_pantone(reader_spot)
        if tintas_planas:
            cobertura_info.append(
                f"<li><span class='icono warn'>🎨</span> Tintas planas detectadas: <b>{', '.join(tintas_planas)}</b></li>"
            )
        else:
            cobertura_info.append(
                "<li><span class='icono error'>❌</span> No se detectaron tintas planas (Pantone)</li>"
            )
    except Exception as e:
        riesgos_info.append(
            f"<li><span class='icono warning'>⚠️</span> Error al verificar tintas planas: {str(e)}</li>"
        )

    overprint_count = detectar_overprints(path_pdf)
    if overprint_count:
        riesgos_info.append(
            f"<li><span class='icono warning'>⚠️</span> Se detectaron <b>{overprint_count}</b> objetos con overprint habilitado. Posibles sobreimpresiones no intencionadas.</li>"
        )

    if not riesgos_info:
        riesgos_info.append(
            "<li><span class='icono ok'>✔️</span> El diseño parece apto para impresión flexográfica con los parámetros ingresados.</li>"
        )

    diagnostico_material = []

    if material_norm == "film":
        negro = cobertura_promedio.get("Negro", 0) if cobertura_promedio else 0
        if negro > 50:
            diagnostico_material.append(
                f"<li><span class='icono warn'>⚠️</span> Cobertura alta de negro (<b>{negro}%</b>). Puede generar problemas de adherencia o secado en film.</li>"
            )
        else:
            diagnostico_material.append(
                "<li><span class='icono ok'>✔️</span> Cobertura de negro adecuada para impresión en film.</li>"
            )
        if tramas_debiles_flag:
            diagnostico_material.append(
                "<li><span class='icono warn'>⚠️</span> Las tramas débiles podrían no transferirse correctamente sobre film.</li>"
            )
    elif material_norm == "papel":
        if textos_pequenos_flag or lineas_finas_flag:
            diagnostico_material.append(
                "<li><span class='icono warn'>⚠️</span> En papel, la ganancia de punto puede afectar textos pequeños y líneas finas.</li>"
            )
        else:
            diagnostico_material.append(
                "<li><span class='icono ok'>✔️</span> No se detectaron elementos sensibles a la ganancia de punto en papel.</li>"
            )
    elif material_norm == "etiqueta adhesiva" and metrics.cobertura_por_canal:
        total_cobertura = sum(metrics.cobertura_por_canal.values())
        if total_cobertura > 240:
            diagnostico_material.append(
                f"<li><span class='icono warn'>⚠️</span> Cobertura total alta (<b>{round(total_cobertura,2)}%</b>). Puede ocasionar problemas de secado en etiquetas adhesivas.</li>"
            )
        else:
            diagnostico_material.append(
                "<li><span class='icono ok'>✔️</span> Cobertura total adecuada para etiqueta adhesiva.</li>"
            )
    elif material_norm:
        diagnostico_material.append(
            f"<li><span class='icono info'>ℹ️</span> Material '<b>{material}</b>' no reconocido. Sin recomendaciones específicas.</li>"
        )

    imagen_tinta = ""
    tinta_data = None
    ink_transfer = None
    tinta_ideal = get_ink_ideal_mlmin(material_norm)
    nivel: int | None = None
    etiqueta = ""
    razones: List[str] = []
    if (
        anilox_bcm is not None
        and velocidad_impresion is not None
        and metrics.cobertura_por_canal
    ):
        try:
            params_tinta = InkParams(
                anilox_lpi=int(float(anilox_lpi) if anilox_lpi is not None else 0),
                anilox_bcm=float(anilox_bcm),
                velocidad_m_min=float(velocidad_impresion),
                ancho_util_m=float(ancho_util_m),
                coef_material=float(material_coef_val),
            )
            ink_transfer = calcular_transmision_tinta(
                params_tinta, metrics.cobertura_por_canal, thresholds
            )
            tinta_ml = ink_transfer.ml_min_global
            nivel, etiqueta, razones = clasificar_riesgo_por_ideal(tinta_ml, tinta_ideal)
            ratio_pct = (tinta_ml / tinta_ideal * 100) if tinta_ideal > 0 else 0
            porcentaje_barra = max(0.0, min(round(ratio_pct, 2), 100.0))
            advertencia_tinta = razones[0] if razones else "Sin observaciones."
            imagen_tinta = generar_grafico_tinta(tinta_ml, tinta_ideal, material)
            tinta_data = {
                "tinta_ml": tinta_ml,
                "barra_pct": porcentaje_barra,
                "advertencia": advertencia_tinta,
                "imagen": imagen_tinta,
                "tinta_por_canal_ml_min": ink_transfer.ml_min_por_canal,
                "tinta_ideal_ml_min": tinta_ideal,
                "ink_risk": {
                    "level": nivel,
                    "label": etiqueta,
                    "reasons": razones,
                },
            }
        except Exception as e:
            tinta_data = {"error": str(e)}
    if nivel is None:
        nivel, etiqueta, razones = clasificar_riesgo_por_ideal(
            ink_transfer.ml_min_global if ink_transfer else None,
            tinta_ideal,
        )

    datos_reporte = {
        "diseno_info": diseno_info,
        "montaje_info": montaje_info,
        "cobertura_info": cobertura_info,
        "riesgos_info": riesgos_info,
        "resolucion_items": resolucion_items,
        "til_items": til_items,
        "capas_items": capas_items,
        "diagnostico_material": diagnostico_material,
    }
    if tinta_data:
        datos_reporte["tinta"] = tinta_data

    resumen = generar_reporte_tecnico(datos_reporte)
    diagnostico_json = {
        "tac_total_v2": metrics.tac_total,
        "tac_p95": metrics.tac_p95,
        "tac_max": metrics.tac_max,
        "cobertura_por_canal": metrics.cobertura_por_canal,
        "cobertura_total": metrics.cobertura_total,
        "tinta_ml_min": ink_transfer.ml_min_global if ink_transfer else None,
        "tinta_por_canal_ml_min": ink_transfer.ml_min_por_canal if ink_transfer else None,
        "tinta_ideal_ml_min": tinta_ideal,
        "ink_risk": {"level": nivel, "label": etiqueta, "reasons": razones},
        "ancho_util_m": ancho_util_m,
        "ancho_mm": ancho_mm,
        "coef_material": material_coef_val,
        "anilox_lpi": anilox_lpi,
        "anilox_bcm": float(anilox_bcm) if anilox_bcm is not None else None,
        "velocidad_impresion": float(velocidad_impresion)
        if velocidad_impresion is not None
        else None,
        "material": material_norm,
    }
    diagnostico_json["sim_base"] = {
        "bcm": float(anilox_bcm) if anilox_bcm is not None else None,
        "vel": float(velocidad_impresion) if velocidad_impresion is not None else None,
        "ancho_m": float(ancho_util_m) if ancho_util_m is not None else None,
        "coef": float(material_coef_val) if material_coef_val is not None else None,
        "tac": float(metrics.tac_total) if metrics.tac_total is not None else None,
    }
    if metrics.cobertura_por_canal:
        diagnostico_json.setdefault("cobertura", dict(metrics.cobertura_por_canal))
    if metrics.tac_total is not None:
        diagnostico_json.setdefault("tac_total", metrics.tac_total)
        diagnostico_json.setdefault("cobertura_estimada", metrics.tac_total)
        diagnostico_json.setdefault("cobertura_base_sum", metrics.tac_total)

    analisis_detallado = {
        "tramas_debiles": tramas_mensajes,
        "cobertura_por_canal": metrics.cobertura_por_canal,
        "textos_pequenos": textos_adv,
        "resolucion_minima": resolucion_minima or 0,
        "trama_minima": 5,
        "cobertura_total": metrics.cobertura_total,
        "tac_total": metrics.tac_total,
        "tac_total_v2": metrics.tac_total,
        "tac_p95": metrics.tac_p95,
        "tac_max": metrics.tac_max,
        "diagnostico_json": diagnostico_json,
    }
    diagnostico_texto = generar_diagnostico_texto(resumen)
    return resumen, imagen_tinta, diagnostico_texto, analisis_detallado, advertencias_overlay


def generar_diagnostico_texto(html_diagnostico: str) -> str:
    """Convierte el diagnóstico en HTML a un texto plano legible."""
    texto = re.sub(r"<[^>]+>", "", html_diagnostico)
    texto = unescape(texto)
    lineas = [line.strip() for line in texto.splitlines() if line.strip()]
    return "\n".join(lineas)


def _strip_html_to_text(value: str) -> str:
    if not value:
        return ""
    texto = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    texto = re.sub(r"</li\s*>", "\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"</p\s*>", "\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = unescape(texto)
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.strip()


def _extract_first_match(texto: str, patrones: List[str]) -> str | None:
    for patron in patrones:
        match = re.search(patron, texto, flags=re.IGNORECASE)
        if match:
            value = next((g for g in match.groups() if g is not None), None)
            if value:
                return " ".join(str(value).split())
    return None


def _collect_warning_lines(*texts: str, limit: int = 5) -> List[str]:
    keywords = (
        "riesgo",
        "advert",
        "problema",
        "warning",
        "trama",
        "texto pequeño",
        "texto pequeno",
        "linea fina",
        "línea fina",
        "sobreimp",
        "sangrado",
        "resolución",
        "resolucion",
        "barniz",
        "troquel",
        "secado",
        "ganancia de punto",
        "baja",
        "alta",
    )
    items: List[str] = []
    seen = set()
    for raw in texts:
        clean = _strip_html_to_text(raw)
        if not clean:
            continue
        for line in clean.splitlines():
            line = " ".join(line.split())
            if not line:
                continue
            low = line.lower()
            if not any(keyword in low for keyword in keywords):
                continue
            line = re.sub(r"^[^\wáéíóúñüÁÉÍÓÚÑÜ]+", "", line)
            if line and line not in seen:
                seen.add(line)
                items.append(line)
            if len(items) >= limit:
                return items
    return items


def _build_sugerencia_produccion_resumen(
    diagnostico_texto: str, resultado_revision: str
) -> str:
    resultado_texto = _strip_html_to_text(resultado_revision)
    diagnostico_plano = _strip_html_to_text(diagnostico_texto)
    corpus = "\n".join(part for part in (resultado_texto, diagnostico_plano) if part)

    material = _extract_first_match(
        corpus,
        [
            r"Material de impresi[oó]n:\s*([^\n]+)",
            r"material\s+'([^']+)'",
        ],
    )
    anilox_lpi = _extract_first_match(
        corpus,
        [
            r"Anilox(?:\s+LPI(?:\s*\(diagn[oó]stico\))?)?:\s*([0-9]+(?:[.,][0-9]+)?)",
            r"Anilox:\s*([0-9]+(?:[.,][0-9]+)?)\s*lpi",
        ],
    )
    bcm = _extract_first_match(
        corpus,
        [
            r"BCM del anilox:\s*([0-9]+(?:[.,][0-9]+)?)",
            r"\bBCM\b[^0-9]*([0-9]+(?:[.,][0-9]+)?)",
        ],
    )
    velocidad = _extract_first_match(
        corpus,
        [
            r"Velocidad(?:\s+estimada\s+de\s+impresi[oó]n|\s+de\s+c[aá]lculo)?:\s*([0-9]+(?:[.,][0-9]+)?)\s*m/min",
        ],
    )
    paso = _extract_first_match(
        corpus,
        [r"Paso del cilindro:\s*([0-9]+(?:[.,][0-9]+)?)\s*mm"],
    )
    tamano = _extract_first_match(
        corpus,
        [r"Tama[nñ]o del dise[nñ]o:\s*([0-9]+(?:[.,][0-9]+)?\s*x\s*[0-9]+(?:[.,][0-9]+)?\s*mm)"],
    )
    cobertura_total = _extract_first_match(
        corpus,
        [r"Cobertura total(?: estimada del dise[nñ]o)?:\s*([0-9]+(?:[.,][0-9]+)?)\s*%"],
    )
    tac_promedio = _extract_first_match(
        corpus,
        [
            r"TAC promedio detectado(?:\s*\(suma CMYK\))?:\s*([0-9]+(?:[.,][0-9]+)?)\s*%",
            r"TAC promedio(?: detectado)?:\s*([0-9]+(?:[.,][0-9]+)?)\s*%",
        ],
    )

    advertencias = _collect_warning_lines(resultado_revision, diagnostico_texto, limit=5)
    problemas_txt = (
        "; ".join(advertencias[:3])
        if advertencias
        else "No se detectaron problemas resumidos."
    )
    advertencias_txt = (
        "; ".join(advertencias)
        if advertencias
        else "Sin advertencias críticas resumibles."
    )

    resumen_lineas = [
        f"Material: {material or 'No disponible'}",
        f"Anilox LPI: {anilox_lpi or 'No disponible'}",
        f"BCM: {bcm or 'No disponible'}",
        f"Velocidad: {velocidad + ' m/min' if velocidad else 'No disponible'}",
        f"Paso del cilindro: {paso + ' mm' if paso else 'No disponible'}",
        f"Tamaño del diseño: {tamano or 'No disponible'}",
        f"Cobertura total: {cobertura_total + '%' if cobertura_total else 'No disponible'}",
        f"TAC promedio: {tac_promedio + '%' if tac_promedio else 'No disponible'}",
        f"Problemas detectados: {problemas_txt}",
        f"Advertencias principales: {advertencias_txt}",
    ]
    return "\n".join(resumen_lineas)


def generar_sugerencia_produccion(diagnostico_texto: str, resultado_revision: str) -> str:
    """Genera sugerencias prácticas de producción basadas en el diagnóstico."""
    try:
        resumen_tecnico = _build_sugerencia_produccion_resumen(
            diagnostico_texto, resultado_revision
        )
        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un especialista en producción de impresión flexográfica. "
                    "Brinda recomendaciones prácticas basadas en el diagnóstico entregado. "
                    "Responde en español, de forma corta, clara, técnica y orientada a producción flexográfica. "
                    "Limita la respuesta a un bloque breve con recomendaciones accionables. "
                    "Evalúa si el archivo está listo para impresión, riesgos en máquina, tipo de anilox según cobertura, "
                    "cambios de técnica de impresión, uso de barniz, doble pasada o reducción de colores y ajustes de preprensa."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Genera una recomendación de producción a partir de este resumen técnico.\n\n"
                    f"{resumen_tecnico}"
                ),
            },
        ]
        respuesta = create_chat_completion(
            model="gpt-4",
            messages=mensajes,
            temperature=0.3,
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al obtener sugerencia de producción: {str(e)}"
