import io
import math
import os
import sys
import builtins
import tempfile
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject

MM_TO_PT = 72.0 / 25.4  # milímetros a puntos
EPS_MM = 0.2

# Exponer el módulo en builtins para facilitar pruebas que lo referencian
builtins.montaje_offset_inteligente = sys.modules[__name__]


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
    """Devuelve ancho y alto del primer página de un PDF en milímetros.

    Parameters
    ----------
    path: str
        Ruta al archivo PDF.
    usar_trimbox: bool
        Si es ``True`` y la página posee ``TrimBox`` se utilizará dicho
        rectángulo para obtener las dimensiones. Esto resulta útil cuando se
        desea ignorar un sangrado existente y trabajar únicamente con el área
        de recorte.
    """
    doc = fitz.open(path)
    page = doc[0]
    try:
        bbox = page.trimbox if usar_trimbox and getattr(page, "trimbox", None) else page.rect
    except AttributeError:  # Compatibilidad con versiones antiguas de PyMuPDF
        bbox = page.rect
    ancho_mm = bbox.width * 25.4 / 72
    alto_mm = bbox.height * 25.4 / 72
    doc.close()
    return round(ancho_mm, 2), round(alto_mm, 2)


def _pdf_a_imagen_con_sangrado(
    path: str, sangrado_mm: float, usar_trimbox: bool = False
) -> ImageReader:
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
        img_con_sangrado = ImageOps.expand(img, border=sangrado_px)

        w, h = img.width, img.height
        left = img.crop((0, 0, 1, h)).resize((sangrado_px, h))
        img_con_sangrado.paste(left, (0, sangrado_px))
        right = img.crop((w - 1, 0, w, h)).resize((sangrado_px, h))
        img_con_sangrado.paste(right, (sangrado_px + w, sangrado_px))
        top = img.crop((0, 0, w, 1)).resize((w, sangrado_px))
        img_con_sangrado.paste(top, (sangrado_px, 0))
        bottom = img.crop((0, h - 1, w, h)).resize((w, sangrado_px))
        img_con_sangrado.paste(bottom, (sangrado_px, sangrado_px + h))
        tl = img.crop((0, 0, 1, 1)).resize((sangrado_px, sangrado_px))
        img_con_sangrado.paste(tl, (0, 0))
        tr = img.crop((w - 1, 0, w, 1)).resize((sangrado_px, sangrado_px))
        img_con_sangrado.paste(tr, (sangrado_px + w, 0))
        bl = img.crop((0, h - 1, 1, h)).resize((sangrado_px, sangrado_px))
        img_con_sangrado.paste(bl, (0, sangrado_px + h))
        br = img.crop((w - 1, h - 1, w, h)).resize((sangrado_px, sangrado_px))
        img_con_sangrado.paste(br, (sangrado_px + w, sangrado_px + h))

    img_byte_arr = io.BytesIO()
    img_con_sangrado.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    doc.close()
    return ImageReader(img_byte_arr)


def _render_preview_vectorial(
    archivos_locales,
    posiciones,
    ancho_pliego_mm,
    alto_pliego_mm,
    preview_path,
    dpi=150,
):
    """
    Genera una vista previa REAL del pliego impuesto:
    - Crea un PDF temporal del tamaño del pliego.
    - Coloca cada PDF origen en su rectángulo destino (con rotación si corresponde).
    - Rasteriza a PNG al 'preview_path' con la resolución indicada.
    Requiere que 'posiciones' tenga: archivo (ruta local), x_mm, y_mm, w_mm, h_mm, rotado (bool).
    """
    # 1) Documento temporal y página del tamaño del pliego (en puntos)
    dest = fitz.open()
    page = dest.new_page(
        width=ancho_pliego_mm * 72.0 / 25.4,
        height=alto_pliego_mm * 72.0 / 25.4,
    )

    # 2) Colocar cada elemento PDF en su rect destino
    for pos in posiciones:
        archivo = pos["archivo"]
        x = pos["x_mm"]
        y = pos["y_mm"]
        w = pos["w_mm"]
        h = pos["h_mm"]
        rot = 90 if pos.get("rotado") else 0

        rect_dest = fitz.Rect(
            x * 72.0 / 25.4,
            y * 72.0 / 25.4,
            (x + w) * 72.0 / 25.4,
            (y + h) * 72.0 / 25.4,
        )

        src = fitz.open(archivo)
        try:
            page.show_pdf_page(rect_dest, src, 0, rotate=rot)
        finally:
            src.close()

    # 3) Guardar PDF temporal y rasterizar a PNG
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name

    try:
        dest.save(tmp_pdf_path)
        dest.close()

        doc_tmp = fitz.open(tmp_pdf_path)
        pg = doc_tmp[0]
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = pg.get_pixmap(matrix=mat, alpha=False)
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        pix.save(preview_path)
        doc_tmp.close()
    finally:
        try:
            os.remove(tmp_pdf_path)
        except Exception:
            pass

    return preview_path


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

    if espaciado_horizontal or espaciado_vertical:
        sep_h, sep_v = espaciado_horizontal, espaciado_vertical
    else:
        sep_h, sep_v = _parse_separacion(separacion)

    used_bbox = [None, None, None, None]
    eps_pt = EPS_MM * MM_TO_PT

    margen_izq = float(margen_izq) + lateral_mm
    margen_der = float(margen_der)
    margen_sup = float(margen_sup)
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
    for path, cantidad in diseños:
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

    archivos_locales = [g["archivo"] for g in grupos]

    posiciones: List[Dict[str, float]] = []
    sobrantes: List[Dict[str, float]] = []

    def _expandir_copias() -> List[Dict[str, float]]:
        lista: List[Dict[str, float]] = []
        for g in grupos:
            for _ in range(g["cantidad"]):
                lista.append(
                    {
                        "archivo": g["archivo"],
                        "ancho": g["ancho_real"],
                        "alto": g["alto_real"],
                        "rotado": g["rotado"],
                    }
                )
        return lista

    # --- RAMA MANUAL: si estrategia == "manual" y hay posiciones_manual ---
    if estrategia == "manual" and posiciones_manual:
        # posiciones_manual viene en mm, bottom-left, con w/h = TRIM (sin sangrado)
        # Normaliza a la misma estructura que usa el dibujado final.
        posiciones = []
        archivos_locales = []
        # Construir set de archivos referenciados
        for p in posiciones_manual:
            ruta = p.get("archivo")
            if not ruta and "file_idx" in p:
                # soporte por índice si el frontend lo manda; el caller debe armar diseños en el mismo orden
                ruta = diseños[p["file_idx"]][0]
            if ruta:
                archivos_locales.append(ruta)

        for p in posiciones_manual:
            ruta = p.get("archivo") or diseños[p["file_idx"]][0]
            posiciones.append(
                {
                    "archivo": ruta,
                    "x": float(p["x_mm"]),
                    "y": float(p["y_mm"]),
                    "ancho": float(p["w_mm"]),  # TRIM
                    "alto": float(p["h_mm"]),  # TRIM
                    "rotado": bool(p.get("rot", False)),
                }
            )

        # opcionalmente centrar
        if centrar and posiciones:
            min_x = min(pp["x"] for pp in posiciones)
            max_x = max(pp["x"] + pp["ancho"] + 2 * sangrado for pp in posiciones)
            min_y = min(pp["y"] for pp in posiciones)
            max_y = max(pp["y"] + pp["alto"] + 2 * sangrado for pp in posiciones)
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
                    "x": x,
                    "y": y,
                    "ancho": copia["ancho"],
                    "alto": copia["alto"],
                    "rotado": copia["rotado"],
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
                    "x": x,
                    "y": y,
                    "ancho": copia["ancho"],
                    "alto": copia["alto"],
                    "rotado": copia["rotado"],
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
        # 1) Construir mapping id->ruta PDF real si fuera necesario
        id_to_pdf = {}
        for idx, ruta in enumerate(archivos_locales):
            id_to_pdf[idx] = ruta

        # 2) Normalizar posiciones para preview (asegura claves y tipos)
        posiciones_normalizadas = []
        for p in posiciones:
            x_mm = float(p.get("x_mm", p.get("x", 0)))
            y_mm = float(p.get("y_mm", p.get("y", 0)))
            w_base = float(
                p.get(
                    "w_mm",
                    p.get("ancho_mm", p.get("ancho", p.get("w", 0))),
                )
            )
            h_base = float(
                p.get(
                    "h_mm",
                    p.get("alto_mm", p.get("alto", p.get("h", 0))),
                )
            )
            w_mm = w_base + 2 * sangrado
            h_mm = h_base + 2 * sangrado
            rotado = bool(p.get("rotado", p.get("rot", False)))

            archivo = p.get("archivo")
            if not archivo:
                file_id = p.get("file_id", p.get("idx", p.get("id", None)))
                if file_id is not None and file_id in id_to_pdf:
                    archivo = id_to_pdf[file_id]
            if not archivo:
                archivo = p.get("ruta_pdf")

            posiciones_normalizadas.append(
                {
                    "archivo": archivo,
                    "x_mm": x_mm,
                    "y_mm": y_mm,
                    "w_mm": w_mm,
                    "h_mm": h_mm,
                    "rotado": rotado,
                }
            )

        # 3) Si preview_path está definido, renderizar con PDFs reales (no wireframe)
        try:
            draw_boxes = False
        except NameError:
            pass

        faltan = [
            q
            for q in posiciones_normalizadas
            if not q["archivo"] or not str(q["archivo"]).lower().endswith(".pdf")
        ]
        if faltan:
            print("[PREVIEW] WARNING: posiciones sin archivo PDF:", faltan[:3])

        try:
            dpi = preview_dpi if isinstance(preview_dpi, (int, float)) else 150
        except NameError:
            dpi = 150

        try:
            print(
                "[PREVIEW] sample pos:",
                posiciones_normalizadas[0] if posiciones_normalizadas else "SIN POSICIONES",
            )
        except Exception as e:
            print("[PREVIEW] posiciones vacías:", e)

        _render_preview_vectorial(
            archivos_locales=archivos_locales,
            posiciones=posiciones_normalizadas,
            ancho_pliego_mm=ancho_pliego,
            alto_pliego_mm=alto_pliego,
            preview_path=preview_path,
            dpi=dpi,
        )

        return {
            "ok": True,
            "preview_generated": True,
            "preview_path": preview_path,
            "resumen_html": resumen_html,
            "positions": posiciones_normalizadas if devolver_posiciones else None,
            "sheet_mm": {"w": ancho_pliego, "h": alto_pliego},
        }

    if preview_only:
        """
        Vista previa REAL (WYSIWYG):
        - Crea un PDF temporal del tamaño del pliego.
        - Coloca cada página PDF fuente en su rect destino (con sangrado y rotación).
        - Rasteriza a PNG (bytes) a la resolución deseada.
        - Devuelve (png_bytes, resumen_html) como esperaba routes.py.
        """
        import tempfile
        import fitz  # PyMuPDF

        # DPI deseado para preview (si viene preview_dpi úsalo; si no, 150)
        try:
            dpi = preview_dpi if isinstance(preview_dpi, (int, float)) else 150
        except NameError:
            dpi = 150

        # 1) Documento temporal y página del tamaño del pliego en puntos
        dest = fitz.open()
        page = dest.new_page(
            width=mm_to_pt(ancho_pliego),
            height=mm_to_pt(alto_pliego),
        )

        if posiciones:
            print("[PREVIEW] pos0:", posiciones[0])

        # 2) Colocar cada elemento (usa 'posiciones', que ya tiene 'archivo', 'x', 'y', 'ancho', 'alto', 'rotado')
        for pos in posiciones:
            archivo = pos.get("archivo")
            if not archivo:
                # si por alguna razón faltara, saltar
                continue

            x_pt = mm_to_pt(pos["x"])
            y_pt = mm_to_pt(pos["y"])
            w_total_pt = mm_to_pt(pos["ancho"] + 2 * sangrado)
            h_total_pt = mm_to_pt(pos["alto"] + 2 * sangrado)

            rect_dest = fitz.Rect(x_pt, y_pt, x_pt + w_total_pt, y_pt + h_total_pt)

            try:
                src = fitz.open(archivo)
                page.show_pdf_page(
                    rect_dest, src, 0,
                    rotate=90 if pos.get("rotado") else 0
                )
            finally:
                try:
                    src.close()
                except Exception:
                    pass

        # 3) Guardar a PDF temporal y rasterizar a PNG (devolver bytes)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name

        try:
            dest.save(tmp_pdf_path)
            dest.close()

            tmp_doc = fitz.open(tmp_pdf_path)
            pg = tmp_doc[0]
            scale = dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            pix = pg.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            tmp_doc.close()
        finally:
            try:
                os.remove(tmp_pdf_path)
            except Exception:
                pass

        return png_bytes, resumen_html

    # Creación del PDF final
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet_w_pt = mm_to_pt(ancho_pliego)
    sheet_h_pt = mm_to_pt(alto_pliego)
    c = canvas.Canvas(output_path, pagesize=(sheet_w_pt, sheet_h_pt))

    image_cache: Dict[str, ImageReader] = {}
    bleed_cache: Dict[str, float] = {}
    for pos in posiciones:
        archivo = pos["archivo"]
        if archivo not in image_cache:
            image_cache[archivo] = _pdf_a_imagen_con_sangrado(
                archivo, sangrado, usar_trimbox=usar_trimbox
            )
        img = image_cache[archivo]
        total_w_pt = mm_to_pt(pos["ancho"] + 2 * sangrado)
        total_h_pt = mm_to_pt(pos["alto"] + 2 * sangrado)
        x_pt = mm_to_pt(pos["x"])
        y_pt = mm_to_pt(pos["y"])
        if pos.get("rotado"):
            c.saveState()
            c.translate(x_pt + total_w_pt / 2, y_pt + total_h_pt / 2)
            c.rotate(90)
            c.drawImage(img, -total_h_pt / 2, -total_w_pt / 2, width=total_h_pt, height=total_w_pt)
            c.restoreState()
        else:
            c.drawImage(img, x_pt, y_pt, width=total_w_pt, height=total_h_pt)

        bleed_eff = sangrado
        if sangrado <= 0:
            if archivo not in bleed_cache:
                bleed_cache[archivo] = detectar_sangrado_pdf(archivo)
            bleed_eff = bleed_cache[archivo]
        x_trim_pt = x_pt + mm_to_pt(bleed_eff)
        y_trim_pt = y_pt + mm_to_pt(bleed_eff)
        if sangrado > 0:
            w_trim_pt = mm_to_pt(pos["ancho"])
            h_trim_pt = mm_to_pt(pos["alto"])
        else:
            w_trim_pt = mm_to_pt(pos["ancho"] - 2 * bleed_eff)
            h_trim_pt = mm_to_pt(pos["alto"] - 2 * bleed_eff)
        bleed_pt = max(0.0, bleed_eff) * MM_TO_PT
        _bbox_add(
            used_bbox,
            x_trim_pt - bleed_pt - eps_pt,
            y_trim_pt - bleed_pt - eps_pt,
            x_trim_pt + w_trim_pt + bleed_pt + eps_pt,
            y_trim_pt + h_trim_pt + bleed_pt + eps_pt,
        )
        if cutmarks_por_forma and bleed_eff > 0:
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
    if not preview_only:
        left = mm_to_pt(margen_izq)
        bottom = mm_to_pt(margen_inf)
        right = sheet_w_pt - mm_to_pt(margen_der)
        top = sheet_h_pt - mm_to_pt(margen_sup)
        if marcas_registro:
            def cross(x: float, y: float, s_mm: float = 5) -> None:
                s = mm_to_pt(s_mm)
                c.line(x - s, y, x + s, y)
                c.line(x, y - s, x, y + s)
                _bbox_add(used_bbox, x - s - eps_pt, y - s - eps_pt, x + s + eps_pt, y + s + eps_pt)
            c.setLineWidth(0.3)
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

    if export_area_util and used_bbox[0] is not None:
        recortar_pdf_a_bbox(output_path, output_path, [used_bbox])

    # Resumen HTML opcional
    if resumen_path:
        os.makedirs(os.path.dirname(resumen_path), exist_ok=True)
        with open(resumen_path, "w", encoding="utf-8") as f:
            f.write(resumen_html)

    return output_path
