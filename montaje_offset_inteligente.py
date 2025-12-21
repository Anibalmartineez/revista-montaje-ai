import gc
import math
import os
import sys
import builtins
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject

from pdf_compat import apply_pdf_compat

MM_TO_PT = 72.0 / 25.4  # milímetros a puntos
EPS_MM = 0.2

# Exponer el módulo en builtins para facilitar pruebas que lo referencian
builtins.montaje_offset_inteligente = sys.modules[__name__]


# DPI reducido para previews (configurable vía env)
PREVIEW_DPI = int(os.getenv("PREVIEW_DPI", "144"))  # 120–150 DPI recomendado


@dataclass
class Diseno:
    ruta: str
    # En el flujo del editor visual, ``cantidad`` se interpreta como "formas por pliego"
    # (no como copias totales) para alinear la comunicación con el motor de imposición.
    cantidad: int = 1


@dataclass
class MontajeConfig:
    tamano_pliego: Tuple[float, float]
    separacion: float | Tuple[float, float] = 4.0
    margen_izquierdo: float = 10.0
    margen_derecho: float = 10.0
    margen_superior: float = 10.0
    margen_inferior: float = 10.0
    espaciado_horizontal: float = 0.0
    espaciado_vertical: float = 0.0
    sangrado: Optional[float] = 3.0
    permitir_rotacion: bool = False
    ordenar_tamano: bool = False
    centrar: bool = True
    alinear_filas: bool = False
    forzar_grilla: bool = False
    filas_grilla: Optional[int] = None
    columnas_grilla: Optional[int] = None
    ancho_grilla_mm: Optional[float] = None
    alto_grilla_mm: Optional[float] = None
    pref_orientacion_horizontal: bool = False
    modo_manual: bool = False
    agregar_marcas: bool = False
    es_pdf_final: bool = True
    estrategia: str = "flujo"
    usar_trimbox: bool = False
    debug_grilla: bool = False
    pinza_mm: float = 0.0
    lateral_mm: float = 0.0
    marcas_registro: bool = False
    marcas_corte: bool = False
    cutmarks_por_forma: bool = False
    export_area_util: bool = False
    preview_path: Optional[str] = None
    output_path: str = "output/pliego_offset_inteligente.pdf"
    posiciones_manual: Optional[List[dict]] = None
    devolver_posiciones: bool = False
    resumen_path: Optional[str] = None
    export_compat: Optional[str] = None  # None | "pdfx1a" | "adobe_compatible"
    ctp_config: Optional[dict] = None
    output_mode: str = "raster"


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round((mm / 25.4) * dpi))


def generar_preview_pliego(disenos, positions, hoja_ancho_mm, hoja_alto_mm, preview_path):
    """
    disenos: list[ (ruta_absoluta_pdf, copias) ]
    positions: [{file_idx,x_mm,y_mm,w_mm,h_mm,rot}, ...]
    hoja_*_mm: tamaño del pliego en mm
    preview_path: salida PNG
    """
    dpi = PREVIEW_DPI
    W = mm_to_px(hoja_ancho_mm, dpi)
    H = mm_to_px(hoja_alto_mm, dpi)

    canvas_img = Image.new("L", (W, H), 255)
    cache: Dict[int, Image.Image] = {}

    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)

    for pos in positions:
        idx = pos["file_idx"]
        ruta = disenos[idx][0]

        if idx not in cache:
            with fitz.open(ruta) as doc:
                page = doc[0]
                pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csGRAY)
            img = Image.frombytes("L", (pix.width, pix.height), pix.samples, "raw")
            cache[idx] = img

        src = cache[idx]

        # Dimensiones destino en px
        w_px = mm_to_px(pos["w_mm"], dpi)
        h_px = mm_to_px(pos["h_mm"], dpi)
        if w_px <= 0 or h_px <= 0:
            continue

        # Rotación por posición (grados)
        rot = int(pos.get("rot_deg") or 0) % 360

        # El cliente ya envía w/h coherentes con la rotación; primero rotamos y luego escalamos
        if rot in (90, 270):
            rotated = src.rotate(-rot, resample=Image.BILINEAR, expand=True)
            scaled = rotated.resize((w_px, h_px), Image.BILINEAR)
            del rotated
        else:
            scaled = src.resize((w_px, h_px), Image.BILINEAR)
            if rot:
                scaled = scaled.rotate(-rot, resample=Image.BILINEAR, expand=False)

        x_px = mm_to_px(pos["x_mm"], dpi)
        y_px = mm_to_px(pos["y_mm"], dpi)
        canvas_img.paste(scaled, (x_px, y_px))
        del scaled

    os.makedirs(os.path.dirname(preview_path), exist_ok=True)
    canvas_img.save(preview_path, optimize=True)
    del canvas_img
    cache.clear()
    gc.collect()

    try:
        import psutil, logging

        rss_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        logging.getLogger(__name__).info(f"[PREVIEW] Memoria RSS ~ {rss_mb:.1f} MB")
    except Exception:
        pass


def mm_to_pt(valor: float) -> float:
    return valor * MM_TO_PT


def _bbox_add(bbox, x0, y0, x1, y1):
    if bbox[0] is None:
        bbox[0], bbox[1], bbox[2], bbox[3] = x0, y0, x1, y1
    else:
        bbox[0] = min(bbox[0], x0)
        bbox[1] = min(bbox[1], y0)
        bbox[2] = max(bbox[2], x1)
        bbox[3] = max(bbox[3], y1)


def recortar_pdf_a_bbox(input_path, output_path, page_bboxes_pt):
    """Ajusta cajas PDF a las áreas utilizadas por página."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    num_pages = len(reader.pages)
    for i in range(num_pages):
        page = reader.pages[i]
        bbox = page_bboxes_pt[i] if i < len(page_bboxes_pt) else None
        if bbox and bbox[0] is not None:
            x0, y0, x1, y1 = map(float, bbox)
            rect = RectangleObject([x0, y0, x1, y1])
            page.mediabox = rect
            page.cropbox = rect
            page.trimbox = rect
            page.bleedbox = rect
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


def draw_cutmarks_around_form_reportlab(canvas, x_pt, y_pt, w_pt, h_pt, bleed_mm, stroke_pt=0.25):
    """
    Dibuja 8 líneas (horizontales y verticales) en las 4 esquinas alrededor del
    rectángulo de corte (Trim) definido por ``x_pt``, ``y_pt``, ``w_pt`` y
    ``h_pt``. La longitud de cada marca es ``bleed_mm`` y siempre se dibuja hacia
    afuera del área útil. No se dibuja nada si ``bleed_mm`` es cero o negativo.
    """
    if bleed_mm is None or bleed_mm <= 0:
        return
    L = bleed_mm * MM_TO_PT
    if L <= 0:
        return

    c = canvas
    c.saveState()
    c.setLineWidth(stroke_pt)
    x0, y0 = x_pt, y_pt
    x1, y1 = x_pt + w_pt, y_pt + h_pt

    # horizontales
    c.line(x0 - L, y0, x0, y0)
    c.line(x1, y0, x1 + L, y0)
    c.line(x0 - L, y1, x0, y1)
    c.line(x1, y1, x1 + L, y1)

    # verticales
    c.line(x0, y0 - L, x0, y0)
    c.line(x1, y0 - L, x1, y0)
    c.line(x0, y1, x0, y1 + L)
    c.line(x1, y1, x1, y1 + L)

    c.restoreState()




def draw_professional_cmyk_strip(canvas, x, y, width, height):
    """Dibuja una tira de control CMYK profesional para impresión offset.

    La composición respeta el rectángulo (x, y, width, height) y se centra en
    la lectura del impresor: sólidos CMYK, parches de trama, escala de grises,
    un gris balanceado CMY, líneas finas para enfoque y microtexto de control.
    """

    c = canvas
    c.saveState()

    margin = min(height * 0.1, mm_to_pt(1.5))
    inner_x = x + margin
    inner_y = y + margin
    inner_w = width - 2 * margin
    inner_h = height - 2 * margin

    if inner_w <= 0 or inner_h <= 0:
        c.restoreState()
        return

    patch_h = inner_h * 0.8
    patch_w = patch_h
    patch_y = inner_y + (inner_h - patch_h) / 2.0
    gap = patch_w * 0.25

    patch_defs = [
        ("C100", (1, 0, 0, 0), 1.0),
        ("M100", (0, 1, 0, 0), 1.0),
        ("Y100", (0, 0, 1, 0), 1.0),
        ("K100", (0, 0, 0, 1), 1.0),
        ("C50", (1, 0, 0, 0), 0.5),
        ("M50", (0, 1, 0, 0), 0.5),
        ("Y50", (0, 0, 1, 0), 0.5),
        ("K50", (0, 0, 0, 1), 0.5),
        ("G25", (0, 0, 0, 0.25), None),
        ("G50", (0, 0, 0, 0.50), None),
        ("G75", (0, 0, 0, 0.75), None),
    ]

    def small_cross(cx, cy, size_pt=mm_to_pt(0.8)):
        c.setStrokeColorCMYK(0, 0, 0, 1)
        c.setLineWidth(0.15)
        c.line(cx - size_pt, cy, cx + size_pt, cy)
        c.line(cx, cy - size_pt, cx, cy + size_pt)

    x_cursor = inner_x
    max_x = inner_x + inner_w
    center_y = inner_y + inner_h / 2.0
    patch_count = 0

    running = True
    while running and x_cursor + patch_w <= max_x:
        for _, base_cmyk, level in patch_defs:
            if x_cursor + patch_w > max_x:
                running = False
                break

            if level is None:
                color = base_cmyk
            else:
                color = tuple(v * level for v in base_cmyk)

            c.setFillColorCMYK(*color)
            c.rect(x_cursor, patch_y, patch_w, patch_h, fill=1, stroke=0)

            patch_count += 1
            if patch_count % 6 == 0:
                small_cross(x_cursor + patch_w / 2.0, center_y)

            x_cursor += patch_w + gap

    c.setFillColorCMYK(0, 0, 0, 1)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(
        inner_x + inner_w / 2.0,
        inner_y + inner_h + mm_to_pt(0.5),
        "CONTROL COLOR OFFSET",
    )

    c.restoreState()


def detectar_sangrado_pdf(path: str) -> float:
    """Devuelve el sangrado existente en un PDF en milímetros.

    Se calcula como la diferencia entre ``BleedBox`` y ``TrimBox``. Si no se
    encuentran dichas cajas o el resultado es negativo se devuelve ``0``.
    """
    doc = fitz.open(path)
    page = doc[0]
    try:
        bleed = page.bleedbox
        trim = page.trimbox
    except AttributeError:
        doc.close()
        return 0.0
    if not bleed or not trim:
        doc.close()
        return 0.0
    width_diff = (bleed.width - trim.width) / 2
    height_diff = (bleed.height - trim.height) / 2
    bleed_pt = min(width_diff, height_diff)
    doc.close()
    bleed_mm = bleed_pt * 25.4 / 72.0
    return bleed_mm if bleed_mm > 0 else 0.0


def obtener_dimensiones_pdf(path: str, usar_trimbox: bool = False) -> Tuple[float, float]:
    """Devuelve ancho y alto del primer página de un PDF en milímetros."""
    with fitz.open(path) as doc:
        page = doc[0]
        rect = page.trimbox if usar_trimbox and getattr(page, "trimbox", None) else page.mediabox
        w, h = rect.width, rect.height
    return round(w * 25.4 / 72, 2), round(h * 25.4 / 72, 2)


def _pdf_a_imagen_con_sangrado(
    path: str, sangrado_mm: float, usar_trimbox: bool = False
) -> Image.Image:
    """Rasteriza un PDF y añade un borde de sangrado replicando los bordes.

    Parameters
    ----------
    path: str
        Ruta del PDF.
    sangrado_mm: float
        Cantidad de sangrado a añadir en milímetros.
    usar_trimbox: bool
        Cuando es ``True`` la página se rasteriza usando el ``TrimBox`` en lugar
        del ``MediaBox``. Esto permite recortar un sangrado existente y
        reemplazarlo por uno nuevo.
    """
    doc = fitz.open(path)
    page = doc[0]
    clip = None
    if usar_trimbox and getattr(page, "trimbox", None):
        try:
            clip = page.trimbox
        except AttributeError:
            clip = None
    pix = page.get_pixmap(dpi=300, alpha=False, clip=clip)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    sangrado_px = int((sangrado_mm / 25.4) * 300)
    if sangrado_px <= 0:
        img_con_sangrado = img
    else:
        arr = np.array(img)
        pad_width = (
            (sangrado_px, sangrado_px),
            (sangrado_px, sangrado_px),
            (0, 0),
        )
        try:
            padded = np.pad(arr, pad_width, mode="reflect")
        except ValueError:
            padded = np.pad(arr, pad_width, mode="symmetric")
        img_con_sangrado = Image.fromarray(padded)

    doc.close()
    return img_con_sangrado


def _pdf_a_imagen_trim(path: str, usar_trimbox: bool = True) -> Image.Image:
    """Rasteriza únicamente el área de trim del PDF a 300 dpi.

    Se utiliza para generar el marco de sangrado espejo en modo vector_hybrid
    sin rasterizar el centro del diseño.
    """

    doc = fitz.open(path)
    page = doc[0]
    clip = None
    if usar_trimbox and getattr(page, "trimbox", None):
        try:
            clip = page.trimbox
        except AttributeError:
            clip = None
    pix = page.get_pixmap(dpi=300, alpha=False, clip=clip)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def _render_vector_hybrid_bleed(path: str, bleed_mm: float, usar_trimbox: bool = True) -> Image.Image:
    """Genera un marco de sangrado espejo alrededor del trim.

    Retorna una imagen RGBA con el centro transparente y únicamente los bordes
    y esquinas rasterizados mediante espejo. Se utiliza exclusivamente para
    el modo ``vector_hybrid``.
    """

    if bleed_mm <= 0:
        raise ValueError("El sangrado debe ser positivo para generar el marco")

    trim_img = _pdf_a_imagen_trim(path, usar_trimbox=usar_trimbox)
    bleed_px = int(round((bleed_mm / 25.4) * 300))
    if bleed_px <= 0:
        raise ValueError("El sangrado en píxeles debe ser positivo")

    trim_w, trim_h = trim_img.size
    frame_w = trim_w + 2 * bleed_px
    frame_h = trim_h + 2 * bleed_px

    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))

    strip_w = min(bleed_px, trim_w)
    strip_h = min(bleed_px, trim_h)

    left_src = trim_img.crop((0, 0, strip_w, trim_h)).transpose(Image.FLIP_LEFT_RIGHT)
    frame.paste(left_src.convert("RGBA"), (0, bleed_px))

    right_src = trim_img.crop((trim_w - strip_w, 0, trim_w, trim_h)).transpose(Image.FLIP_LEFT_RIGHT)
    frame.paste(right_src.convert("RGBA"), (bleed_px + trim_w, bleed_px))

    top_src = trim_img.crop((0, 0, trim_w, strip_h)).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(top_src.convert("RGBA"), (bleed_px, 0))

    bottom_src = trim_img.crop((0, trim_h - strip_h, trim_w, trim_h)).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(bottom_src.convert("RGBA"), (bleed_px, bleed_px + trim_h))

    tl_src = trim_img.crop((0, 0, strip_w, strip_h)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(tl_src.convert("RGBA"), (0, 0))

    tr_src = trim_img.crop((trim_w - strip_w, 0, trim_w, strip_h)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(tr_src.convert("RGBA"), (bleed_px + trim_w, 0))

    bl_src = trim_img.crop((0, trim_h - strip_h, strip_w, trim_h)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(bl_src.convert("RGBA"), (0, bleed_px + trim_h))

    br_src = trim_img.crop((trim_w - strip_w, trim_h - strip_h, trim_w, trim_h)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    frame.paste(br_src.convert("RGBA"), (bleed_px + trim_w, bleed_px + trim_h))

    return frame


def _parse_separacion(separacion: float | Tuple[float, float] | Dict[str, float]) -> Tuple[float, float]:
    """Devuelve separación horizontal y vertical en mm."""
    if isinstance(separacion, dict):
        sep_h = float(separacion.get("horizontal", separacion.get("x", 0)))
        sep_v = float(separacion.get("vertical", separacion.get("y", sep_h)))
    elif isinstance(separacion, (list, tuple)):
        if len(separacion) == 2:
            sep_h, sep_v = map(float, separacion)
        else:
            sep_h = sep_v = float(separacion[0])
    else:
        sep_h = sep_v = float(separacion)
    return sep_h, sep_v


def calcular_posiciones(
    disenos: List[Dict[str, float]],
    ancho_pliego: float,
    alto_pliego: float,
    margen: float = 10,
    separacion: float = 5,
    sangrado: float = 0,
    centrar: bool = False,
    alinear_filas: bool = False,
    forzar_grilla: bool = False,
    debug: bool = False,
) -> List[Dict[str, float]]:
    """Calcula posiciones de cada diseño evitando solapamientos.

    Parámetros
    ----------
    disenos: lista de dicts con ``archivo``, ``ancho`` y ``alto``.
    forzar_grilla: cuando es ``True`` se genera una grilla tipo tabla donde
        * cada columna tiene el ancho del diseño más grande de esa columna y
        * cada fila tiene la altura del diseño más alto de esa fila.
        Esto garantiza cortes rectos y alineados aun con tamaños diferentes.
    debug: si está activo se devuelve en cada posición el tamaño de la celda
        calculada (``celda_ancho`` y ``celda_alto``) para poder dibujar guías.
    """

    posiciones: List[Dict[str, float]] = []

    if forzar_grilla and disenos:
        # Primero distribuimos los diseños en filas según el ancho disponible
        ancho_disponible = ancho_pliego - 2 * margen
        filas: List[List[Dict[str, float]]] = []
        fila_actual: List[Dict[str, float]] = []
        ancho_acumulado = 0.0
        for d in disenos:
            ancho_total = d["ancho"] + 2 * sangrado
            if fila_actual and ancho_acumulado + ancho_total > ancho_disponible:
                filas.append(fila_actual)
                fila_actual = []
                ancho_acumulado = 0.0
            fila_actual.append({**d, "ancho_total": ancho_total, "alto_total": d["alto"] + 2 * sangrado})
            ancho_acumulado += ancho_total + separacion
        if fila_actual:
            filas.append(fila_actual)

        # Calculamos altos por fila y anchos por columna para definir la grilla
        altos_fila = [max(f["alto_total"] for f in fila) for fila in filas]
        num_columnas = max(len(fila) for fila in filas)
        anchos_columna: List[float] = []
        for col in range(num_columnas):
            max_ancho = 0.0
            for fila in filas:
                if len(fila) > col:
                    max_ancho = max(max_ancho, fila[col]["ancho_total"])
            anchos_columna.append(max_ancho)

        # Posiciones acumuladas de cada columna y fila
        x_cols = []
        x_cursor = margen
        for ancho_col in anchos_columna:
            x_cols.append(x_cursor)
            x_cursor += ancho_col + separacion

        y_filas = []
        y_cursor = alto_pliego - margen
        for alto_f in altos_fila:
            y_filas.append(y_cursor)
            y_cursor -= alto_f + separacion
        # Si no cabe verticalmente, dejamos de colocar filas excedentes

        for i, fila in enumerate(filas):
            if y_filas[i] - altos_fila[i] < margen:
                break
            for j, diseno in enumerate(fila):
                if j >= len(x_cols):
                    break
                x = x_cols[j]
                top_y = y_filas[i]
                y = top_y - diseno["alto_total"]  # alineado al borde superior
                pos = {
                    "archivo": diseno["archivo"],
                    "x": x,
                    "y": y,
                    "ancho": diseno["ancho"],
                    "alto": diseno["alto"],
                }
                if debug:
                    pos["celda_ancho"] = anchos_columna[j]
                    pos["celda_alto"] = altos_fila[i]
                posiciones.append(pos)
    elif alinear_filas and disenos:
        ancho_celda = max(d["ancho"] + 2 * sangrado for d in disenos)
        alto_celda = max(d["alto"] + 2 * sangrado for d in disenos)
        ancho_disponible = ancho_pliego - 2 * margen
        max_columnas = max(1, int(ancho_disponible / (ancho_celda + separacion)))

        for idx, diseno in enumerate(disenos):
            columna = idx % max_columnas
            fila = idx // max_columnas
            x = margen + columna * (ancho_celda + separacion)
            y = (
                alto_pliego
                - margen
                - alto_celda
                - fila * (alto_celda + separacion)
            )
            if y < margen:
                break
            pos = {
                "archivo": diseno["archivo"],
                "x": x,
                "y": y,
                "ancho": diseno["ancho"],
                "alto": diseno["alto"],
            }
            if debug:
                pos["celda_ancho"] = ancho_celda
                pos["celda_alto"] = alto_celda
            posiciones.append(pos)
    else:
        # Comenzamos desde la esquina superior izquierda (orden tradicional)
        x_cursor = margen
        y_cursor = alto_pliego - margen
        fila_max_altura = 0

        for diseno in disenos:
            ancho_total = diseno["ancho"] + 2 * sangrado
            alto_total = diseno["alto"] + 2 * sangrado

            # Si no entra en la fila actual pasamos a la siguiente fila
            if x_cursor + ancho_total > ancho_pliego - margen:
                x_cursor = margen
                y_cursor -= fila_max_altura + separacion
                fila_max_altura = 0

            # Si no entra verticalmente dejamos de colocar diseños
            if y_cursor - alto_total < margen:
                break

            pos = {
                "archivo": diseno["archivo"],
                "x": x_cursor,
                # Convertimos a coordenadas de origen inferior izquierdo
                "y": y_cursor - alto_total,
                "ancho": diseno["ancho"],
                "alto": diseno["alto"],
            }
            if debug:
                pos["celda_ancho"] = ancho_total
                pos["celda_alto"] = alto_total
            posiciones.append(pos)

            x_cursor += ancho_total + separacion
            fila_max_altura = max(fila_max_altura, alto_total)

    if centrar and posiciones:
        min_x = min(p["x"] for p in posiciones)
        max_x = max(p["x"] + p["ancho"] + 2 * sangrado for p in posiciones)
        min_y = min(p["y"] for p in posiciones)
        max_y = max(p["y"] + p["alto"] + 2 * sangrado for p in posiciones)
        usado_w = max_x - min_x
        usado_h = max_y - min_y
        espacio_h = ancho_pliego - usado_w
        espacio_v = alto_pliego - usado_h
        desplaz_x = espacio_h / 2 - min_x
        desplaz_y = espacio_v / 2 - min_y
        for p in posiciones:
            p["x"] += desplaz_x
            p["y"] += desplaz_y

    # Reporte simple de aprovechamiento
    area_total_util = (ancho_pliego - 2 * margen) * (alto_pliego - 2 * margen)
    area_usada = sum(
        (p["ancho"] + 2 * sangrado) * (p["alto"] + 2 * sangrado)
        for p in posiciones
    )
    if area_total_util > 0:
        porcentaje = area_usada / area_total_util * 100
        print(
            f"Se colocaron {len(posiciones)} diseños, ocupando {porcentaje:.1f}% del área útil"
        )

    return posiciones


def agregar_marcas_registro(c: canvas.Canvas, sheet_w_pt: float, sheet_h_pt: float) -> None:
    mark_len = mm_to_pt(5)
    offset = mm_to_pt(5)
    x = sheet_w_pt / 2
    c.setLineWidth(0.3)
    for y in (offset, sheet_h_pt - offset):
        c.line(x - mark_len, y, x + mark_len, y)
        c.line(x, y - mark_len, x, y + mark_len)
        c.circle(x, y, mm_to_pt(1), stroke=1, fill=0)


class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h


class MaxRects:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.free_rects: List[Rect] = [Rect(0, 0, width, height)]

    def insert(self, width: float, height: float) -> Tuple[float, float] | None:
        best_index = -1
        best_short = math.inf
        best_long = math.inf
        best_rect: Rect | None = None
        for i, r in enumerate(self.free_rects):
            if r.w >= width and r.h >= height:
                leftover_h = r.h - height
                leftover_w = r.w - width
                short_side = min(leftover_w, leftover_h)
                long_side = max(leftover_w, leftover_h)
                if short_side < best_short or (
                    short_side == best_short and long_side < best_long
                ):
                    best_index = i
                    best_rect = r
                    best_short = short_side
                    best_long = long_side
        if best_index == -1 or best_rect is None:
            return None
        placed = Rect(best_rect.x, best_rect.y, width, height)
        self._split_free_rect(best_rect, placed)
        del self.free_rects[best_index]
        self._prune_free_list()
        return placed.x, placed.y

    def _split_free_rect(self, free: Rect, used: Rect) -> None:
        if (
            used.x >= free.x + free.w
            or used.x + used.w <= free.x
            or used.y >= free.y + free.h
            or used.y + used.h <= free.y
        ):
            return
        if used.x < free.x + free.w and used.x + used.w > free.x:
            if used.y > free.y:
                self.free_rects.append(
                    Rect(free.x, free.y, free.w, used.y - free.y)
                )
            if used.y + used.h < free.y + free.h:
                self.free_rects.append(
                    Rect(
                        free.x,
                        used.y + used.h,
                        free.w,
                        free.y + free.h - (used.y + used.h),
                    )
                )
        if used.y < free.y + free.h and used.y + used.h > free.y:
            if used.x > free.x:
                self.free_rects.append(
                    Rect(free.x, free.y, used.x - free.x, free.h)
                )
            if used.x + used.w < free.x + free.w:
                self.free_rects.append(
                    Rect(
                        used.x + used.w,
                        free.y,
                        free.x + free.w - (used.x + used.w),
                        free.h,
                    )
                )

    def _prune_free_list(self) -> None:
        i = 0
        while i < len(self.free_rects):
            j = i + 1
            while j < len(self.free_rects):
                if self._is_contained_in(self.free_rects[i], self.free_rects[j]):
                    del self.free_rects[i]
                    i -= 1
                    break
                if self._is_contained_in(self.free_rects[j], self.free_rects[i]):
                    del self.free_rects[j]
                else:
                    j += 1
            i += 1

    @staticmethod
    def _is_contained_in(a: Rect, b: Rect) -> bool:
        return (
            a.x >= b.x
            and a.y >= b.y
            and a.x + a.w <= b.x + b.w
            and a.y + a.h <= b.y + b.h
        )


def realizar_montaje_inteligente(
    diseno_list: List[Diseno],
    config: MontajeConfig,
):
    """Ejecuta el montaje inteligente usando ``MontajeConfig``.

    Expande la lista de diseños según su ``cantidad`` y delega en
    :func:`montar_pliego_offset_inteligente` para mantener la lógica
    existente.
    """

    if not diseno_list:
        raise ValueError("La lista de diseños no puede estar vacía")

    disenos: List[Tuple[str, int]] = []
    for d in diseno_list:
        if not d:
            continue
        copias = int(d.cantidad)
        if copias <= 0:
            continue
        disenos.append((d.ruta, copias))
    if not disenos:
        raise ValueError("Se requieren al menos una copia de algún diseño")

    estrategia_actual = config.estrategia
    auto_mode = estrategia_actual == "auto"
    if auto_mode:
        from ai_strategy_selector import select_strategy

        estrategia_actual = select_strategy(disenos, config)

    if config.modo_manual or config.posiciones_manual:
        estrategia_actual = "manual"
    elif config.forzar_grilla and estrategia_actual != "manual":
        estrategia_actual = "grid"

    config.estrategia = estrategia_actual

    from strategies import get_strategy

    strategy = get_strategy(estrategia_actual)
    meta: Dict[str, Any] = {"auto": auto_mode, "estrategia_final": estrategia_actual}
    return strategy.calcular(disenos, config, meta)


def montar_pliego_offset_inteligente(
    diseños: List[Tuple[str, int]],
    ancho_pliego: float,
    alto_pliego: float,
    separacion: float | Tuple[float, float] = 4,
    sangrado: float = 3,
    usar_trimbox: bool = False,
    ordenar_tamano: bool = False,
    permitir_rotacion: bool = False,
    alinear_filas: bool = False,
    preferir_horizontal: bool = False,
    centrar: bool = True,
    debug_grilla: bool = False,
    espaciado_horizontal: float = 0,
    espaciado_vertical: float = 0,
    margen_izq: float = 10,
    margen_der: float = 10,
    margen_sup: float = 10,
    margen_inf: float = 10,
    estrategia: str = "flujo",
    filas: int = 0,
    columnas: int = 0,
    celda_ancho: float = 0,
    celda_alto: float = 0,
    pinza_mm: float = 0.0,
    lateral_mm: float = 0.0,
    marcas_registro: bool = False,
    marcas_corte: bool = False,
    cutmarks_por_forma: bool = False,
    export_area_util: bool = False,
    preview_only: bool = False,
    output_path: str = "output/pliego_offset_inteligente.pdf",
    preview_path: str | None = None,
    posiciones_manual: list[dict] | None = None,
    devolver_posiciones: bool = False,
    resumen_path: str | None = None,
    ctp_config: dict | None = None,
    output_mode: str = "raster",
    **kwargs,
) -> str | Tuple[bytes, str]:
    """Genera un PDF montando múltiples diseños con lógica profesional.

    Devuelve la ruta del PDF generado. También puede generar una imagen de
    vista previa y un reporte HTML si se indican las rutas ``preview_path`` y
    ``resumen_path``. Si ``permitir_rotacion`` es ``True`` se evaluará rotar
    cada diseño 90° para aumentar la cantidad de copias por fila. El parámetro
    ``usar_trimbox`` permite recortar los PDFs a su ``TrimBox`` antes de añadir
    el sangrado indicado, lo cual resulta útil para reemplazar un sangrado
    existente por uno nuevo.

    Parameters
    ----------
    posiciones_manual: list[dict] | None, optional
        Posiciones ya calculadas en milímetros (bottom-left) para usar en la
        imposición manual. Cada diccionario debe incluir ``x_mm``, ``y_mm``,
        ``w_mm`` y ``h_mm`` (trim) además de ``archivo`` o ``file_idx``.
    devolver_posiciones: bool, optional
        Cuando es ``True`` y se genera una vista previa, se incluyen las
        posiciones normalizadas en la respuesta para que el frontend pueda
        utilizarlas.
    """

    preview_path = kwargs.get("preview_path", preview_path)
    output_path = kwargs.get("output_pdf_path", output_path)
    posiciones_manual = kwargs.get("posiciones_override", posiciones_manual)
    export_compat = kwargs.get("export_compat")
    ctp_config = kwargs.get("ctp_config", ctp_config)
    output_mode = (kwargs.get("output_mode", output_mode) or "raster").lower()
    if posiciones_manual is not None:
        estrategia = "manual"

    if espaciado_horizontal or espaciado_vertical:
        sep_h, sep_v = espaciado_horizontal, espaciado_vertical
    else:
        sep_h, sep_v = _parse_separacion(separacion)

    used_bbox = [None, None, None, None]
    eps_pt = EPS_MM * MM_TO_PT
    ctp_cfg = ctp_config or {}
    ctp_enabled = bool(ctp_cfg.get("enabled"))
    gripper_mm = float(ctp_cfg.get("gripper_mm", 0) or 0)
    block_bbox_pt = [None, None, None, None]

    margen_izq = float(margen_izq) + lateral_mm
    margen_der = float(margen_der)
    margen_sup = float(margen_sup)
    # ⚠️ LÓGICA NUEVA DE PINZA / MARGEN INFERIOR
    if ctp_enabled:
        # Si Producción / CTP está activo, el margen inferior real del pliego
        # DEBE SER exactamente el valor de "Pinza inferior (mm)" del editor visual.
        margen_inf = float(gripper_mm)
    else:
        # Comportamiento clásico: margen inferior base + pinza_mm configurada
        margen_inf = float(margen_inf) + pinza_mm

    ancho_util = ancho_pliego - margen_izq - margen_der

    if estrategia == "maxrects":
        preferir_horizontal = False
        alinear_filas = False
    elif estrategia == "grid":
        alinear_filas = False

    # Recolectamos dimensiones de cada diseño evaluando rotación
    grupos = []
    max_unit_w = 0.0
    max_unit_h = 0.0
    for file_idx, (path, cantidad) in enumerate(diseños):
        ancho, alto = obtener_dimensiones_pdf(path, usar_trimbox=usar_trimbox)
        rotado = False
        if permitir_rotacion:
            unit_w = ancho + 2 * sangrado
            unit_w_rot = alto + 2 * sangrado
            forms_x = int((ancho_util + sep_h) / (unit_w + sep_h))
            forms_x_rot = int((ancho_util + sep_h) / (unit_w_rot + sep_h))
            if preferir_horizontal:
                if alto > ancho and forms_x_rot >= forms_x:
                    rotado = True
            elif forms_x_rot > forms_x:
                rotado = True
        real_ancho = alto if rotado else ancho
        real_alto = ancho if rotado else alto
        grupos.append(
            {
                "archivo": path,
                "file_idx": file_idx,
                "ancho": ancho,
                "alto": alto,
                "ancho_real": real_ancho,
                "alto_real": real_alto,
                "cantidad": int(cantidad),
                "rotado": rotado,
            }
        )
        max_unit_w = max(max_unit_w, real_ancho + 2 * sangrado)
        max_unit_h = max(max_unit_h, real_alto + 2 * sangrado)

    if ordenar_tamano:
        grupos.sort(key=lambda g: g["ancho_real"] * g["alto_real"], reverse=True)

    posiciones: List[Dict[str, float]] = []
    sobrantes: List[Dict[str, float]] = []

    def _idx_from_basename_safe(basename: str) -> int | None:
        base = basename.lower()
        for i, (ruta_pdf, *_) in enumerate(diseños):
            ruta_lower = ruta_pdf.lower()
            if ruta_lower == base or os.path.basename(ruta_lower) == base:
                return i
        return None

    def _expandir_copias() -> List[Dict[str, float]]:
        lista: List[Dict[str, float]] = []
        for g in grupos:
            for _ in range(g["cantidad"]):
                lista.append(
                    {
                        "archivo": g["archivo"],
                        "file_idx": g["file_idx"],
                        "ancho": g["ancho_real"],
                        "alto": g["alto_real"],
                        "rotado": g["rotado"],
                    }
                )
        return lista

    # --- RAMA MANUAL: si estrategia == "manual" y hay posiciones_manual ---
    if estrategia == "manual" and posiciones_manual:
        # posiciones_manual viene en mm, bottom-left, con w/h = TRIM (sin sangrado)
        # Para repeat, el slot ya representa la caja final con bleed incluido; el bleed
        # de salida solo afecta contenido interno y marcas, no el tamaño externo.
        # Normaliza a la misma estructura que usa el dibujado final.
        posiciones = []
        for p in posiciones_manual:
            idx = int(p["file_idx"])
            assert 0 <= idx < len(diseños), f"file_idx fuera de rango: {idx}"
            ruta = diseños[idx][0]
            # Resolver sangrado efectivo con esta prioridad:
            # 1) p["bleed_mm"] (precalculado por _sanitize_layout_items)
            # 2) p["bleed_override_mm"] (override directo del editor)
            # 3) sangrado (global del montaje)
            # 4) 0.0 mm como último recurso

            raw_bleed_mm = p.get("bleed_mm")
            raw_bleed_override = p.get("bleed_override_mm")

            bleed_effective = None

            # 1) usar bleed_mm si viene definido
            try:
                if raw_bleed_mm is not None and raw_bleed_mm != "":
                    bleed_effective = float(raw_bleed_mm)
            except Exception:
                bleed_effective = None

            # 2) si no hay bleed_mm válido, usar override
            if bleed_effective is None:
                try:
                    if raw_bleed_override is not None and raw_bleed_override != "":
                        bleed_effective = float(raw_bleed_override)
                except Exception:
                    bleed_effective = None

            # 3) si tampoco hay override válido, usar sangrado global
            if bleed_effective is None and sangrado is not None:
                try:
                    bleed_effective = float(sangrado)
                except Exception:
                    bleed_effective = None

            # 4) último recurso
            if bleed_effective is None:
                bleed_effective = 0.0
            slot_box_final = bool(p.get("slot_box_final"))
            final_w_mm = float(p["w_mm"])
            final_h_mm = float(p["h_mm"])
            if slot_box_final:
                bleed_effective = min(
                    float(bleed_effective),
                    final_w_mm / 2.0 if final_w_mm > 0 else 0.0,
                    final_h_mm / 2.0 if final_h_mm > 0 else 0.0,
                )
            base_w_mm = final_w_mm
            base_h_mm = final_h_mm
            if slot_box_final:
                base_w_mm = max(0.1, final_w_mm - 2 * bleed_effective)
                base_h_mm = max(0.1, final_h_mm - 2 * bleed_effective)

            posiciones.append(
                {
                    "archivo": ruta,        # informativo, no usar para enlazar
                    "file_idx": idx,        # clave estable para enlazar al PDF correcto
                    "x": float(p["x_mm"]),
                    "y": float(p["y_mm"]),
                    "ancho": base_w_mm,  # TRIM
                    "alto": base_h_mm,  # TRIM
                    "rot_deg": int(p.get("rot_deg", p.get("rot", 0)) or 0) % 360,
                    "bleed_mm": float(bleed_effective) if bleed_effective is not None else 0.0,
                }
            )

        # opcionalmente centrar
        if centrar and posiciones and not ctp_enabled:
            min_x = min(pp["x"] for pp in posiciones)
            max_x = max(pp["x"] + pp["ancho"] + 2 * pp.get("bleed_mm", sangrado) for pp in posiciones)
            min_y = min(pp["y"] for pp in posiciones)
            max_y = max(pp["y"] + pp["alto"] + 2 * pp.get("bleed_mm", sangrado) for pp in posiciones)
            usado_w = max_x - min_x
            usado_h = max_y - min_y
            desplaz_x = (ancho_pliego - usado_w) / 2 - min_x
            desplaz_y = (alto_pliego - usado_h) / 2 - min_y
            for pp in posiciones:
                pp["x"] += desplaz_x
                pp["y"] += desplaz_y

        # Sobrantes no aplican aquí (el usuario decide)
        sobrantes = []

    elif estrategia == "grid":
        copias = _expandir_copias()
        ancho_util = ancho_pliego - margen_izq - margen_der
        alto_util = alto_pliego - margen_sup - margen_inf
        if celda_ancho > 0 and celda_alto > 0:
            celda_w = celda_ancho + 2 * sangrado
            celda_h = celda_alto + 2 * sangrado
            columnas_calc = max(1, int((ancho_util + sep_h) / (celda_w + sep_h)))
            filas_calc = max(1, int((alto_util + sep_v) / (celda_h + sep_v)))
            cols = columnas_calc
            rows = filas_calc
            cell_w = celda_w
            cell_h = celda_h
        else:
            cols = max(1, columnas)
            rows = max(1, filas)
            cell_w = (ancho_util - (cols - 1) * sep_h) / cols
            cell_h = (alto_util - (rows - 1) * sep_v) / rows
        for idx, copia in enumerate(copias):
            row = idx // cols
            col = idx % cols
            if row >= rows:
                sobrantes.append({"archivo": copia["archivo"], "cantidad": 1})
                continue
            total_w = copia["ancho"] + 2 * sangrado
            total_h = copia["alto"] + 2 * sangrado
            if total_w > cell_w or total_h > cell_h:
                sobrantes.append({"archivo": copia["archivo"], "cantidad": 1})
                continue
            offset_x = (cell_w - total_w) / 2
            offset_y = (cell_h - total_h) / 2
            x = margen_izq + col * (cell_w + sep_h) + offset_x
            top_y = alto_pliego - margen_sup - row * (cell_h + sep_v)
            y = top_y - cell_h + offset_y
            posiciones.append(
                {
                    "archivo": copia["archivo"],
                    "file_idx": copia["file_idx"],
                    "x": x,
                    "y": y,
                    "ancho": copia["ancho"],
                    "alto": copia["alto"],
                    "rotado": copia["rotado"],
                    "bleed_mm": sangrado,
                }
            )
    elif estrategia == "maxrects":
        copias = _expandir_copias()
        ancho_util = ancho_pliego - margen_izq - margen_der
        alto_util = alto_pliego - margen_sup - margen_inf
        packer = MaxRects(ancho_util, alto_util)
        for copia in copias:
            rect_w = copia["ancho"] + 2 * sangrado + sep_h
            rect_h = copia["alto"] + 2 * sangrado + sep_v
            pos = packer.insert(rect_w, rect_h)
            if pos is None:
                sobrantes.append({"archivo": copia["archivo"], "cantidad": 1})
                continue
            x = margen_izq + pos[0] + sep_h / 2
            y = margen_inf + pos[1] + sep_v / 2
            posiciones.append(
                {
                    "archivo": copia["archivo"],
                    "file_idx": copia["file_idx"],
                    "x": x,
                    "y": y,
                    "ancho": copia["ancho"],
                    "alto": copia["alto"],
                    "rotado": copia["rotado"],
                    "bleed_mm": sangrado,
                }
            )
    else:
        y_cursor = alto_pliego - margen_sup
        for g in grupos:
            unit_w = g["ancho_real"] + 2 * sangrado
            unit_h = g["alto_real"] + 2 * sangrado
            if alinear_filas:
                unit_h = max_unit_h

            if unit_w > ancho_util:
                sobrantes.append({"archivo": g["archivo"], "cantidad": g["cantidad"]})
                continue

            forms_x = int((ancho_util + sep_h) / (unit_w + sep_h))
            forms_x = max(1, forms_x)

            restante = g["cantidad"]
            while restante > 0:
                alto_disponible = y_cursor - margen_inf
                max_rows = int((alto_disponible + sep_v) / (unit_h + sep_v))
                if max_rows <= 0:
                    break

                forms_y = min(max_rows, math.ceil(restante / forms_x))
                copias = min(restante, forms_x * forms_y)
                top_y = y_cursor

                for idx in range(copias):
                    col = idx % forms_x
                    row = idx // forms_x
                    x = margen_izq + col * (unit_w + sep_h)
                    y = top_y - unit_h - row * (unit_h + sep_v)

                    offset_y = 0.0
                    if alinear_filas:
                        offset_y = (unit_h - (g["alto_real"] + 2 * sangrado)) / 2

                    posiciones.append(
                        {
                            "archivo": g["archivo"],
                            "file_idx": g["file_idx"],
                            "x": x,
                            "y": y + offset_y,
                            "ancho": g["ancho_real"],
                            "alto": g["alto_real"],
                            "rotado": g["rotado"],
                        }
                    )

                block_height = forms_y * unit_h + (forms_y - 1) * sep_v
                y_cursor = top_y - block_height - sep_v * 2
                restante -= copias

                if restante > 0 and y_cursor - margen_inf < unit_h:
                    break

            if restante > 0:
                sobrantes.append({"archivo": g["archivo"], "cantidad": restante})
                if y_cursor - margen_inf < unit_h:
                    break

    if centrar and posiciones and not (ctp_enabled and posiciones_manual):
        min_x = min(p["x"] for p in posiciones)
        max_x = max(p["x"] + p["ancho"] + 2 * sangrado for p in posiciones)
        min_y = min(p["y"] for p in posiciones)
        max_y = max(p["y"] + p["alto"] + 2 * sangrado for p in posiciones)
        usado_w = max_x - min_x
        usado_h = max_y - min_y
        espacio_h = ancho_pliego - usado_w
        espacio_v = alto_pliego - usado_h
        desplaz_x = espacio_h / 2 - min_x
        desplaz_y = espacio_v / 2 - min_y
        for p in posiciones:
            p["x"] += desplaz_x
            p["y"] += desplaz_y

    area_usada = sum(
        (p["ancho"] + 2 * sangrado) * (p["alto"] + 2 * sangrado) for p in posiciones
    )

    total_disenos = sum(c[1] for c in diseños)
    colocados_total = len(posiciones)
    area_total = (ancho_pliego - margen_izq - margen_der) * (
        alto_pliego - margen_sup - margen_inf
    )
    porcentaje = 0.0
    if area_total > 0:
        porcentaje = area_usada / area_total * 100
    advertencias = ""
    if sobrantes:
        faltantes = ", ".join(
            f"{s['archivo']} ({s['cantidad']} copias)" for s in sobrantes
        )
        advertencias = f"No se pudieron colocar: {faltantes}"
    marcas = []
    if marcas_registro:
        marcas.append("registro")
    if marcas_corte:
        marcas.append("corte")
    marcas_txt = ", ".join(marcas) if marcas else "ninguna"
    resumen_html = f"""
    <html><body>
    <h1>Resumen de montaje</h1>
    <p>Pliego: {ancho_pliego} x {alto_pliego} mm</p>
    <p>Diseños colocados: {colocados_total} de {total_disenos}</p>
    <p>Uso del pliego: {porcentaje:.1f}%</p>
    <p>Reserva pinza: {pinza_mm} mm, lateral: {lateral_mm} mm</p>
    <p>Marcas añadidas: {marcas_txt}</p>
    <p>{advertencias}</p>
    </body></html>
    """

    # Si viene preview_path, generar SOLO la vista previa real con los PDFs originales
    if preview_path:
        posiciones_normalizadas = []
        for p in posiciones:
            x_mm = float(p.get("x_mm", p.get("x", 0)))
            y_mm = float(p.get("y_mm", p.get("y", 0)))
            w_base = float(p.get("w_mm", p.get("ancho_mm", p.get("ancho", p.get("w", 0)))))
            h_base = float(p.get("h_mm", p.get("alto_mm", p.get("alto", p.get("h", 0)))))
            bleed_mm = p.get("bleed_mm", sangrado)
            try:
                bleed_mm = float(bleed_mm)
            except Exception:
                bleed_mm = sangrado
            w_mm = w_base + 2 * (bleed_mm or 0)
            h_mm = h_base + 2 * (bleed_mm or 0)
            rot_deg = int(p.get("rot_deg", p.get("rot", 0)) or 0) % 360

            idx = p.get("file_idx")
            if idx is None:
                ruta = p.get("archivo") or p.get("ruta_pdf", "")
                guess = _idx_from_basename_safe(os.path.basename(ruta))
                if guess is None:
                    raise ValueError("No se pudo resolver file_idx desde basename")
                idx = int(guess)
            else:
                idx = int(idx)
            assert 0 <= idx < len(diseños), f"file_idx fuera de rango al render: {idx}"

            posiciones_normalizadas.append(
                {
                    "file_idx": idx,
                    "x_mm": x_mm,
                    "y_mm": y_mm,
                    "w_mm": w_mm,
                    "h_mm": h_mm,
                    "rot_deg": rot_deg,
                }
            )

        generar_preview_pliego(
            disenos=diseños,
            positions=posiciones_normalizadas,
            hoja_ancho_mm=ancho_pliego,
            hoja_alto_mm=alto_pliego,
            preview_path=preview_path,
        )

        result = {
            "preview_path": preview_path,
            "resumen_html": resumen_html if 'resumen_html' in locals() else None,
        }
        if devolver_posiciones:
            positions_norm = []
            for p in posiciones:
                idx = p.get("file_idx")
                if idx is None:
                    ruta = p.get("archivo") or p.get("ruta_pdf", "")
                    guess = _idx_from_basename_safe(os.path.basename(ruta))
                    if guess is None:
                        raise ValueError("No se pudo resolver file_idx desde basename")
                    idx = int(guess)
                else:
                    idx = int(idx)
                assert 0 <= idx < len(diseños), f"file_idx fuera de rango: {idx}"
                positions_norm.append(
                    {
                        "file_idx": idx,
                        # conservar también la ruta original para que routes.py
                        # pueda reconstruir el índice si es necesario
                        "archivo": p.get("archivo"),
                        "ruta_pdf": p.get("archivo"),
                        "x_mm": p["x"],
                        "y_mm": p["y"],
                        "w_mm": p["ancho"],
                        "h_mm": p["alto"],
                        "rot_deg": int(p.get("rot_deg", 0)) % 360,
                    }
                )
            result["positions"] = positions_norm
            result["sheet_mm"] = {"w": ancho_pliego, "h": alto_pliego}
        return result

    if preview_only:
        import tempfile

        posiciones_normalizadas = []
        for p in posiciones:
            idx = p.get("file_idx")
            if idx is None:
                ruta = p.get("archivo") or p.get("ruta_pdf", "")
                guess = _idx_from_basename_safe(os.path.basename(ruta))
                if guess is None:
                    raise ValueError("No se pudo resolver file_idx desde basename")
                idx = int(guess)
            else:
                idx = int(idx)
            assert 0 <= idx < len(diseños), f"file_idx fuera de rango al render: {idx}"
            bleed_effective = p.get("bleed_mm", sangrado)
            if bleed_effective is None:
                bleed_effective = 0.0
            w_mm = p["ancho"] + 2 * bleed_effective
            h_mm = p["alto"] + 2 * bleed_effective
            posiciones_normalizadas.append(
                {
                    "file_idx": idx,
                    # conservar la ruta original igual que en devolver_posiciones
                    "archivo": p.get("archivo"),
                    "ruta_pdf": p.get("archivo"),
                    "x_mm": p["x"],
                    "y_mm": p["y"],
                    "w_mm": w_mm,
                    "h_mm": h_mm,
                    "rot_deg": int(p.get("rot_deg", 0)) % 360,
                    "bleed_mm": bleed_effective,
                }
            )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
            tmp_path = tmp_png.name

        try:
            generar_preview_pliego(
                disenos=diseños,
                positions=posiciones_normalizadas,
                hoja_ancho_mm=ancho_pliego,
                hoja_alto_mm=alto_pliego,
                preview_path=tmp_path,
            )
            with open(tmp_path, "rb") as fh:
                png_bytes = fh.read()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        if devolver_posiciones:
            return {
                "preview_bytes": png_bytes,
                "resumen_html": resumen_html,
                "positions": posiciones_normalizadas,
                "sheet_mm": {"w": float(ancho_pliego), "h": float(alto_pliego)},
            }

        return png_bytes, resumen_html

    # Creación del PDF final
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet_w_pt = mm_to_pt(ancho_pliego)
    sheet_h_pt = mm_to_pt(alto_pliego)
    c = canvas.Canvas(output_path, pagesize=(sheet_w_pt, sheet_h_pt))

    image_cache: Dict[tuple[str, float], Image.Image] = {}
    bleed_cache: Dict[str, float] = {}
    bleed_frame_cache: Dict[tuple[str, float], Image.Image] = {}
    vector_overlays: list[dict] = []
    is_vector_hybrid = output_mode == "vector_hybrid"
    for pos in posiciones:
        idx = pos.get("file_idx")
        if idx is None:
            ruta = pos.get("archivo") or pos.get("ruta_pdf", "")
            guess = _idx_from_basename_safe(os.path.basename(ruta))
            if guess is None:
                raise ValueError("No se pudo resolver file_idx desde basename")
            idx = int(guess)
        else:
            idx = int(idx)
        assert 0 <= idx < len(diseños), f"file_idx fuera de rango al render: {idx}"
        archivo = diseños[idx][0]
        bleed_effective = pos.get("bleed_mm", sangrado)
        if bleed_effective is None:
            bleed_effective = 0.0
        cache_key = (archivo, float(bleed_effective))
        draw_raster = True
        img = None
        if is_vector_hybrid:
            draw_raster = bleed_effective > 0
            if draw_raster:
                if cache_key not in bleed_frame_cache:
                    bleed_frame_cache[cache_key] = _render_vector_hybrid_bleed(
                        archivo,
                        bleed_effective,
                        usar_trimbox=True,
                    )
                img = bleed_frame_cache[cache_key]
        else:
            if draw_raster:
                if cache_key not in image_cache:
                    image_cache[cache_key] = _pdf_a_imagen_con_sangrado(
                        archivo,
                        bleed_effective,
                        usar_trimbox=(bleed_effective > 0 or usar_trimbox),
                    )
                img = image_cache[cache_key]
        base_w_mm = pos["ancho"]
        base_h_mm = pos["alto"]
        cx_mm = pos["x"] + base_w_mm / 2.0
        cy_mm = pos["y"] + base_h_mm / 2.0
        draw_w_mm = base_w_mm + 2 * bleed_effective
        draw_h_mm = base_h_mm + 2 * bleed_effective
        trim_w_mm = base_w_mm
        trim_h_mm = base_h_mm
        rot = int(pos.get("rot_deg") or 0) % 360
        swapped = rot in (90, 270)

        eff_draw_w_mm = draw_h_mm if swapped else draw_w_mm
        eff_draw_h_mm = draw_w_mm if swapped else draw_h_mm
        eff_trim_w_mm = trim_h_mm if swapped else trim_w_mm
        eff_trim_h_mm = trim_w_mm if swapped else trim_h_mm

        x_draw_mm = cx_mm - eff_draw_w_mm / 2.0
        y_draw_mm = cy_mm - eff_draw_h_mm / 2.0

        x_pt = mm_to_pt(x_draw_mm)
        y_pt = mm_to_pt(y_draw_mm)
        w_pt = mm_to_pt(eff_draw_w_mm)
        h_pt = mm_to_pt(eff_draw_h_mm)

        if draw_raster and img is not None:
            if rot:
                img_to_draw = img.rotate(-rot, resample=Image.BILINEAR, expand=True)
            else:
                img_to_draw = img

            draw_kwargs = {"width": w_pt, "height": h_pt}
            if getattr(img_to_draw, "mode", "") == "RGBA":
                draw_kwargs["mask"] = "auto"
            c.drawImage(ImageReader(img_to_draw), x_pt, y_pt, **draw_kwargs)

        bleed_eff = bleed_effective
        if bleed_effective is None or bleed_effective <= 0:
            if archivo not in bleed_cache:
                bleed_cache[archivo] = detectar_sangrado_pdf(archivo)
            bleed_eff = bleed_cache[archivo]
        x_trim_mm = x_draw_mm + bleed_eff
        y_trim_mm = y_draw_mm + bleed_eff

        overlay_x_mm = x_draw_mm + bleed_effective
        overlay_y_mm = y_draw_mm + bleed_effective

        if is_vector_hybrid:
            vector_overlays.append(
                {
                    "path": archivo,
                    "x_mm": overlay_x_mm,
                    "y_mm": overlay_y_mm,
                    "w_mm": eff_trim_w_mm,
                    "h_mm": eff_trim_h_mm,
                    "rot_deg": rot,
                }
            )
        x_trim_pt = mm_to_pt(x_trim_mm)
        y_trim_pt = mm_to_pt(y_trim_mm)
        if bleed_effective > 0:
            w_trim_pt = mm_to_pt(eff_trim_w_mm)
            h_trim_pt = mm_to_pt(eff_trim_h_mm)
        else:
            w_trim_pt = mm_to_pt(eff_trim_w_mm - 2 * bleed_eff)
            h_trim_pt = mm_to_pt(eff_trim_h_mm - 2 * bleed_eff)
        bleed_pt = max(0.0, bleed_eff) * MM_TO_PT
        _bbox_add(
            used_bbox,
            x_trim_pt - bleed_pt - eps_pt,
            y_trim_pt - bleed_pt - eps_pt,
            x_trim_pt + w_trim_pt + bleed_pt + eps_pt,
            y_trim_pt + h_trim_pt + bleed_pt + eps_pt,
        )
        _bbox_add(block_bbox_pt, x_pt, y_pt, x_pt + w_pt, y_pt + h_pt)
        if cutmarks_por_forma and bleed_eff > 0 and pos.get("crop_marks", True):
            draw_cutmarks_around_form_reportlab(
                canvas=c,
                x_pt=x_trim_pt,
                y_pt=y_trim_pt,
                w_pt=w_trim_pt,
                h_pt=h_trim_pt,
                bleed_mm=bleed_eff,
                stroke_pt=0.25,
            )

    image_cache.clear()
    bleed_frame_cache.clear()
    if not preview_only:
        left = mm_to_pt(margen_izq)
        bottom = mm_to_pt(margen_inf)
        right = sheet_w_pt - mm_to_pt(margen_der)
        top = sheet_h_pt - mm_to_pt(margen_sup)
        marks_cfg = {}
        if ctp_enabled and block_bbox_pt[0] is not None:
            marks_cfg = (ctp_cfg.get("marks") or {}) if isinstance(ctp_cfg, dict) else {}
            tech_cfg = (ctp_cfg.get("technical_text") or {}) if isinstance(ctp_cfg, dict) else {}

            # -------- TIRA CMYK SUPERIOR (solo si está activada) --------
            if marks_cfg.get("control_strip"):
                c.saveState()
                strip_height_pt = mm_to_pt(12)
                strip_offset_pt = mm_to_pt(2)

                strip_y = min(
                    sheet_h_pt - strip_height_pt - strip_offset_pt,
                    block_bbox_pt[3] + strip_offset_pt,
                )
                strip_y = max(strip_y, block_bbox_pt[1])

                strip_x = block_bbox_pt[0]
                strip_width_pt = block_bbox_pt[2] - block_bbox_pt[0]

                draw_professional_cmyk_strip(
                    canvas=c,
                    x=strip_x,
                    y=strip_y,
                    width=strip_width_pt,
                    height=strip_height_pt,
                )
                c.restoreState()

            # -------- TEXTO TÉCNICO EN PINZA --------
            job_name = str(tech_cfg.get("job_name") or "").strip()
            client = str(tech_cfg.get("client") or "").strip()
            notes = str(tech_cfg.get("notes") or "").strip()
            extra_text = str(tech_cfg.get("extra_text") or "").strip()
            auto_cmyk = bool(tech_cfg.get("auto_cmyk", True))

            base_y = mm_to_pt(max(gripper_mm * 0.4, 3))
            max_y = sheet_h_pt - mm_to_pt(4)
            text_y = min(base_y, max_y)

            c.saveState()
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.15, 0.15, 0.15)

            x_text = mm_to_pt(5)

            line1_parts = []
            if client:
                line1_parts.append(f"CLIENTE: {client}")
            if job_name:
                line1_parts.append(f"TRABAJO: {job_name}")
            line1 = " – ".join(line1_parts) if line1_parts else ""
            if line1:
                c.drawString(x_text, text_y, line1)

            if notes:
                c.drawString(x_text, text_y + mm_to_pt(3), notes)

            if extra_text:
                c.drawString(x_text, text_y + mm_to_pt(6), extra_text)

            # Texto CMYK automático (C M Y K en su canal)
            if auto_cmyk:
                try:
                    c.setFont("Helvetica-Bold", 9)
                    base_x_cmyk = sheet_w_pt - mm_to_pt(40)
                    y_cmyk = text_y

                    # C
                    c.setFillColorCMYK(1, 0, 0, 0)
                    c.drawString(base_x_cmyk, y_cmyk, "C")
                    # M
                    c.setFillColorCMYK(0, 1, 0, 0)
                    c.drawString(base_x_cmyk + mm_to_pt(4), y_cmyk, "M")
                    # Y
                    c.setFillColorCMYK(0, 0, 1, 0)
                    c.drawString(base_x_cmyk + mm_to_pt(8), y_cmyk, "Y")
                    # K
                    c.setFillColorCMYK(0, 0, 0, 1)
                    c.drawString(base_x_cmyk + mm_to_pt(12), y_cmyk, "K")
                except Exception:
                    c.setFillColorRGB(0.1, 0.1, 0.1)
                    c.drawString(sheet_w_pt - mm_to_pt(30), y_cmyk, "CMYK")

            c.restoreState()

        if marks_cfg.get("registro"):
            marcas_registro = True
        if marcas_registro:
            def cross(x: float, y: float, s_mm: float = 5) -> None:
                s = mm_to_pt(s_mm)
                c.line(x - s, y, x + s, y)
                c.line(x, y - s, x, y + s)
                _bbox_add(used_bbox, x - s - eps_pt, y - s - eps_pt, x + s + eps_pt, y + s + eps_pt)
            c.setLineWidth(0.3)
            if ctp_enabled and block_bbox_pt[0] is not None:
                offset_pt = mm_to_pt(10)
                block_left, block_bottom, block_right, block_top = block_bbox_pt
                x_left = max(mm_to_pt(3), block_left - offset_pt)
                x_right = min(sheet_w_pt - mm_to_pt(3), block_right + offset_pt)
                y_bottom = max(mm_to_pt(3), block_bottom - offset_pt)
                y_top = min(sheet_h_pt - mm_to_pt(3), block_top + offset_pt)
                cross(x_left, y_bottom)
                cross(x_left, y_top)
                cross(x_right, y_bottom)
                cross(x_right, y_top)
            else:
                cross(left, bottom)
                cross(left, top)
                cross(right, bottom)
                cross(right, top)

        if marcas_corte:
            mark = mm_to_pt(5)
            c.setLineWidth(0.3)
            c.line(left, bottom - mark, left, bottom)
            c.line(left - mark, bottom, left, bottom)
            _bbox_add(used_bbox, left - mark - eps_pt, bottom - mark - eps_pt, left + eps_pt, bottom + eps_pt)
            c.line(right, bottom - mark, right, bottom)
            c.line(right + mark, bottom, right, bottom)
            _bbox_add(used_bbox, right - eps_pt, bottom - mark - eps_pt, right + mark + eps_pt, bottom + eps_pt)
            c.line(left, top, left, top + mark)
            c.line(left - mark, top, left, top)
            _bbox_add(used_bbox, left - mark - eps_pt, top - eps_pt, left + eps_pt, top + mark + eps_pt)
            c.line(right, top, right, top + mark)
            c.line(right, top, right + mark, top)
            _bbox_add(used_bbox, right - eps_pt, top - eps_pt, right + mark + eps_pt, top + mark + eps_pt)

        c.setStrokeColorRGB(0, 0, 0)
    c.save()

    if is_vector_hybrid and vector_overlays:
        tmp_out = output_path + ".tmp.pdf"
        try:
            with fitz.open(output_path) as target_doc:
                page = target_doc[0]

                for overlay in vector_overlays:
                    with fitz.open(overlay["path"]) as src_doc:
                        src_page = src_doc[0]
                        clip_rect = None
                        try:
                            clip_rect = src_page.trimbox
                        except Exception:
                            clip_rect = None
                        if clip_rect is None:
                            try:
                                clip_rect = src_page.cropbox
                            except Exception:
                                clip_rect = None
                        if clip_rect is None:
                            clip_rect = src_page.mediabox

                        target_rect = fitz.Rect(
                            mm_to_pt(overlay["x_mm"]),
                            mm_to_pt(overlay["y_mm"]),
                            mm_to_pt(overlay["x_mm"] + overlay["w_mm"]),
                            mm_to_pt(overlay["y_mm"] + overlay["h_mm"]),
                        )
                        page.show_pdf_page(
                            target_rect,
                            src_doc,
                            0,
                            rotate=int(overlay.get("rot_deg", 0)) % 360,
                            clip=clip_rect,
                        )

                target_doc.save(tmp_out, incremental=False)
            os.replace(tmp_out, output_path)
        finally:
            try:
                if os.path.exists(tmp_out):
                    os.remove(tmp_out)
            except Exception:
                pass

    if export_area_util and used_bbox[0] is not None:
        recortar_pdf_a_bbox(output_path, output_path, [used_bbox])

    if export_compat:
        try:
            new_path = apply_pdf_compat(output_path, export_compat)
            if new_path:
                output_path = new_path
        except Exception as e:
            print("[WARN] PDF compat post-process failed:", e)

    # Resumen HTML opcional
    if resumen_path:
        os.makedirs(os.path.dirname(resumen_path), exist_ok=True)
        with open(resumen_path, "w", encoding="utf-8") as f:
            f.write(resumen_html)

    if devolver_posiciones:
        positions_norm = []
        for p in posiciones:
            idx = p.get("file_idx")
            if idx is None:
                ruta = p.get("archivo") or p.get("ruta_pdf", "")
                guess = _idx_from_basename_safe(os.path.basename(ruta))
                if guess is None:
                    raise ValueError("No se pudo resolver file_idx desde basename")
                idx = int(guess)
            else:
                idx = int(idx)
            assert 0 <= idx < len(diseños), f"file_idx fuera de rango al render: {idx}"
            positions_norm.append(
                {
                    "file_idx": idx,
                    # igual que en las otras ramas, conserva la ruta
                    "archivo": p.get("archivo"),
                    "ruta_pdf": p.get("archivo"),
                    "x_mm": float(p["x"]),
                    "y_mm": float(p["y"]),
                    "w_mm": float(p["ancho"]),
                    "h_mm": float(p["alto"]),
                    "rot_deg": int(p.get("rot_deg", 0)) % 360,
                }
            )
        return {
            "output_path": output_path,
            "positions": positions_norm,
            "sheet_mm": {"w": float(ancho_pliego), "h": float(alto_pliego)},
        }

    return output_path


def _sanitize_slot_bleed(
    slot: dict,
    design_ref: str | None,
    design_export: dict | None,
    export_settings: dict | None,
    bleed_default: float,
    work: dict | None = None,
) -> float:
    bleed_val = None
    if isinstance(export_settings, dict):
        bleed_val = export_settings.get("bleed_mm")

    if bleed_val is None and design_ref is not None:
        design_overrides = (design_export or {}).get(str(design_ref))
        if isinstance(design_overrides, dict):
            bleed_val = design_overrides.get("bleed_mm")

    if bleed_val is None:
        bleed_val = slot.get("bleed_mm")

    if bleed_val is None and work:
        bleed_val = work.get("default_bleed_mm")
    if bleed_val is None:
        bleed_val = bleed_default
    try:
        return float(bleed_val)
    except (TypeError, ValueError):
        return float(bleed_default)


def _resolve_slot_crop_marks(
    slot: dict, design_ref: str | None, design_export: dict | None, export_settings: dict | None
) -> bool:
    crop_val = None
    if isinstance(export_settings, dict):
        crop_val = export_settings.get("crop_marks")
        if crop_val is not None:
            return bool(crop_val)

    if design_ref is not None:
        design_overrides = (design_export or {}).get(str(design_ref))
        if isinstance(design_overrides, dict):
            crop_val = design_overrides.get("crop_marks")

    if crop_val is None:
        crop_val = slot.get("crop_marks")

    if crop_val is None:
        crop_val = True
    return bool(crop_val)


def montar_offset_desde_layout(layout_data, job_dir, preview: bool = False):
    """
    layout_data viene del layout_constructor.json.
    job_dir es la carpeta static/constructor_offset_jobs/<job_id>/.
    Si preview=True: genera un PNG y devuelve su ruta.
    Si preview=False: genera un PDF final y devuelve su ruta.
    """

    if layout_data is None:
        raise ValueError("layout_data es requerido")

    sheet_mm = layout_data.get("sheet_mm", [640, 880])
    margins = layout_data.get("margins_mm", [10, 10, 10, 10])
    bleed_default_raw = layout_data.get("bleed_default_mm")
    try:
        bleed_default = float(bleed_default_raw)
    except (TypeError, ValueError):
        bleed_default = 3.0
    bleed_layout = bleed_default
    gap_default = layout_data.get("gap_default_mm", 0)
    ctp_cfg = layout_data.get("ctp", {}) or {}
    ctp_enabled = bool(ctp_cfg.get("enabled"))
    gripper_mm = float(ctp_cfg.get("gripper_mm", 0) or 0)
    base_pinza_mm = float(layout_data.get("pinza_mm", 0) or 0)
    export_settings_raw = layout_data.get("export_settings")
    export_settings = export_settings_raw if isinstance(export_settings_raw, dict) else {}
    output_mode = str(export_settings.get("output_mode", "raster")).lower()
    design_export_raw = layout_data.get("design_export")
    design_export = design_export_raw if isinstance(design_export_raw, dict) else {}
    # Manual sanity: Diseño bleed=3 → export bleed=1 produce PDF con 1mm; export crop off produce PDF sin marcas.

    designs = layout_data.get("designs", []) or []
    works = {w.get("id"): w for w in (layout_data.get("works", []) or [])}
    ref_to_idx: Dict[str, int] = {}
    disenos: List[Diseno] = []

    for d in designs:
        filename = d.get("filename")
        ref = d.get("ref")
        if not filename or not ref:
            continue
        ruta_pdf = os.path.join(job_dir, filename)
        if not os.path.exists(ruta_pdf):
            continue
        ref_to_idx[str(ref)] = len(disenos)
        forms_per_plate = max(1, int(d.get("forms_per_plate") or 1))
        disenos.append(Diseno(ruta=ruta_pdf, cantidad=forms_per_plate))

    engine_name = (layout_data.get("imposition_engine") or "repeat").lower()

    def _positions_for_face(target_face: str) -> tuple[list[dict], bool]:
        posiciones: List[dict] = []
        face_crop = False
        for slot in layout_data.get("slots", []) or []:
            slot_face = (slot.get("face") or "front").lower()
            if slot_face != target_face:
                continue
            ref = slot.get("design_ref")
            if not ref or ref not in ref_to_idx:
                continue
            work = works.get(slot.get("logical_work_id"))
            bleed_val = _sanitize_slot_bleed(
                slot, ref, design_export, export_settings, bleed_default, work
            )
            w_mm = float(slot.get("w_mm", 0))
            h_mm = float(slot.get("h_mm", 0))
            has_bleed = bool(work.get("has_bleed")) if work else False

            if has_bleed:
                # Consideramos que w_mm/h_mm ya incluyen el sangrado completo
                trim_w = w_mm
                trim_h = h_mm
            else:
                if engine_name == "repeat":
                    # Antes restábamos bleed_default otra vez y eso abría un gap fijo (p. ej. 3 mm) entre slots.
                    trim_w = w_mm
                    trim_h = h_mm
                else:
                    trim_w = w_mm - 2 * bleed_layout if w_mm else 0
                    trim_h = h_mm - 2 * bleed_layout if h_mm else 0
            if trim_w <= 0:
                trim_w = max(1.0, w_mm)
            if trim_h <= 0:
                trim_h = max(1.0, h_mm)
            crop_flag = _resolve_slot_crop_marks(slot, ref, design_export, export_settings)
            face_crop = face_crop or crop_flag
            posiciones.append(
                {
                    "file_idx": ref_to_idx[ref],
                    "x_mm": float(slot.get("x_mm", slot.get("x", 0))),
                    "y_mm": float(slot.get("y_mm", slot.get("y", 0))),
                    "w_mm": trim_w,
                    "h_mm": trim_h,
                    "rot_deg": int(slot.get("rotation_deg", slot.get("rot_deg", 0)) or 0),
                    "bleed_mm": bleed_val,
                    "crop_marks": crop_flag,
                    # Para repeat, el slot ya es la caja final con bleed incluido.
                    "slot_box_final": engine_name == "repeat",
                }
            )
        return posiciones, face_crop

    def _strategy_from_engine(layout_obj: dict) -> str:
        engine = (layout_obj.get("imposition_engine") or "repeat").lower()
        if engine == "nesting":
            return "nesting_pro"
        if engine == "hybrid":
            return "hybrid_nesting_repeat"
        return "grid"

    front_positions, front_crop = _positions_for_face("front")
    back_positions, back_crop = _positions_for_face("back")
    has_front = len(front_positions) > 0
    has_back = len(back_positions) > 0

    margin_left, margin_right, margin_top, margin_bottom = margins if len(margins) == 4 else (10, 10, 10, 10)
    preview_path = os.path.join(job_dir, "preview.png") if preview else None
    output_path = os.path.join(job_dir, "montaje_final.pdf")

    def _config_for_positions(
        posiciones: List[dict],
        crop_flag: bool,
        output: str,
        preview_target: str | None,
        estrategia_nombre: str,
    ):
        modo_manual = bool(posiciones)
        return MontajeConfig(
            tamano_pliego=tuple(sheet_mm),
            separacion=gap_default,
            margen_izquierdo=margin_left,
            margen_derecho=margin_right,
            margen_superior=margin_top,
            margen_inferior=margin_bottom,
            pinza_mm=gripper_mm if ctp_enabled else base_pinza_mm,
            sangrado=bleed_default,
            cutmarks_por_forma=crop_flag,
            posiciones_manual=posiciones if modo_manual else None,
            modo_manual=modo_manual,
            estrategia="manual" if modo_manual else estrategia_nombre,
            es_pdf_final=not preview,
            preview_path=preview_target,
            output_path=output,
            ctp_config=ctp_cfg,
            output_mode=output_mode,
        )

    def _resolve_output_path(res, default_path: str) -> str:
        if isinstance(res, str):
            return res
        if isinstance(res, dict):
            return res.get("output_path", default_path)
        return default_path

    if not disenos:
        # No hay diseños asignados; solo devuelve la ruta esperada
        if preview:
            return preview_path
        return output_path

    estrategia_nombre = _strategy_from_engine(layout_data)

    if preview:
        preview_positions = front_positions if has_front else back_positions
        preview_crop = front_crop if has_front else back_crop
        preview_config = _config_for_positions(
            preview_positions, preview_crop, output_path, preview_path, estrategia_nombre
        )
        res = realizar_montaje_inteligente(disenos, preview_config)
        if isinstance(res, dict):
            return res.get("preview_path", preview_path)
        return preview_path

    if not has_back or not has_front:
        target_positions = front_positions if has_front else back_positions
        crop_flag = front_crop if has_front else back_crop
        config = _config_for_positions(target_positions, crop_flag, output_path, None, estrategia_nombre)
        res = realizar_montaje_inteligente(disenos, config)
        if isinstance(res, dict):
            return res.get("output_path", output_path)
        if isinstance(res, str):
            return res
        return output_path

    front_output = os.path.join(job_dir, "montaje_front.pdf")
    back_output = os.path.join(job_dir, "montaje_back.pdf")

    front_config = _config_for_positions(front_positions, front_crop, front_output, None, estrategia_nombre)
    back_config = _config_for_positions(back_positions, back_crop, back_output, None, estrategia_nombre)

    front_res = realizar_montaje_inteligente(disenos, front_config)
    back_res = realizar_montaje_inteligente(disenos, back_config)

    front_path = _resolve_output_path(front_res, front_output)
    back_path = _resolve_output_path(back_res, back_output)

    writer = PdfWriter()
    for pdf_path in (front_path, back_path):
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as fh:
        writer.write(fh)

    return output_path
