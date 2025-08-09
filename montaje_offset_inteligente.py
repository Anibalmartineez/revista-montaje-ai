import io
import math
import os
import sys
import builtins
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

MM_TO_PT = 2.83465  # milímetros a puntos

# Exponer el módulo en builtins para facilitar pruebas que lo referencian
builtins.montaje_offset_inteligente = sys.modules[__name__]


def mm_to_pt(valor: float) -> float:
    return valor * MM_TO_PT


def obtener_dimensiones_pdf(path: str) -> Tuple[float, float]:
    """Devuelve ancho y alto del primer página de un PDF en milímetros."""
    doc = fitz.open(path)
    page = doc[0]
    bbox = page.rect
    ancho_mm = bbox.width * 25.4 / 72
    alto_mm = bbox.height * 25.4 / 72
    doc.close()
    return round(ancho_mm, 2), round(alto_mm, 2)


def _pdf_a_imagen_con_sangrado(path: str, sangrado_mm: float) -> ImageReader:
    """Rasteriza un PDF y añade un borde de sangrado replicando los bordes."""
    doc = fitz.open(path)
    page = doc[0]
    pix = page.get_pixmap(dpi=300, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    sangrado_px = int((sangrado_mm / 25.4) * 300)
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
    ordenar_tamano: bool = False,
    permitir_rotacion: bool = False,
    alinear_filas: bool = False,  # compatibilidad, no usado
    centrar: bool = False,
    forzar_grilla: bool = False,  # compatibilidad con versiones previas
    debug_grilla: bool = False,
    espaciado_horizontal: float = 0,
    espaciado_vertical: float = 0,
    margen_izq: float = 10,
    margen_der: float = 10,
    margen_sup: float = 10,
    margen_inf: float = 10,
    doble_corte: bool | None = None,
    estrategia: str = "flujo",
    filas: int = 0,
    columnas: int = 0,
    celda_ancho: float = 0,
    celda_alto: float = 0,
    output_path: str = "output/pliego_offset_inteligente.pdf",
    preview_path: str | None = None,
    resumen_path: str | None = None,
) -> str:
    """Genera un PDF montando múltiples diseños con lógica profesional.

    Devuelve la ruta del PDF generado. También puede generar una imagen de
    vista previa y un reporte HTML si se indican las rutas ``preview_path`` y
    ``resumen_path``. Si ``permitir_rotacion`` es ``True`` se evaluará rotar
    cada diseño 90° para aumentar la cantidad de copias por fila.
    """

    if doble_corte is None:
        doble_corte = forzar_grilla

    if espaciado_horizontal or espaciado_vertical:
        sep_h, sep_v = espaciado_horizontal, espaciado_vertical
    else:
        sep_h, sep_v = _parse_separacion(separacion)

    margen_izq, margen_der, margen_sup, margen_inf = (
        float(margen_izq),
        float(margen_der),
        float(margen_sup),
        float(margen_inf),
    )

    ancho_util = ancho_pliego - margen_izq - margen_der

    # Recolectamos dimensiones de cada diseño evaluando rotación
    grupos = []
    max_unit_w = 0.0
    max_unit_h = 0.0
    for path, cantidad in diseños:
        ancho, alto = obtener_dimensiones_pdf(path)
        rotado = False
        if permitir_rotacion:
            unit_w = ancho + 2 * sangrado
            unit_w_rot = alto + 2 * sangrado
            forms_x = int((ancho_util + sep_h) / (unit_w + sep_h))
            forms_x_rot = int((ancho_util + sep_h) / (unit_w_rot + sep_h))
            if forms_x_rot > forms_x:
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
        grupos.sort(key=lambda g: g["ancho"], reverse=True)

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

    if estrategia == "grid":
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
            if doble_corte:
                unit_w = max_unit_w
                unit_h = max_unit_h
            else:
                unit_w = g["ancho_real"] + 2 * sangrado
                unit_h = g["alto_real"] + 2 * sangrado

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

                    offset_x = 0.0
                    offset_y = 0.0
                    if doble_corte:
                        offset_x = (unit_w - (g["ancho_real"] + 2 * sangrado)) / 2
                        offset_y = (unit_h - (g["alto_real"] + 2 * sangrado)) / 2

                    posiciones.append(
                        {
                            "archivo": g["archivo"],
                            "x": x + offset_x,
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

    # Creación del PDF final
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet_w_pt = mm_to_pt(ancho_pliego)
    sheet_h_pt = mm_to_pt(alto_pliego)
    c = canvas.Canvas(output_path, pagesize=(sheet_w_pt, sheet_h_pt))

    area_usada = 0.0
    image_cache: Dict[str, ImageReader] = {}
    for pos in posiciones:
        archivo = pos["archivo"]
        if archivo not in image_cache:
            image_cache[archivo] = _pdf_a_imagen_con_sangrado(archivo, sangrado)
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

        # Marcas de corte
        left = x_pt + mm_to_pt(sangrado)
        bottom = y_pt + mm_to_pt(sangrado)
        right = left + mm_to_pt(pos["ancho"])
        top = bottom + mm_to_pt(pos["alto"])
        mark_len = mm_to_pt(3)
        c.setLineWidth(0.3)
        c.setStrokeColorRGB(1, 0, 0)
        c.line(left - mark_len, bottom, left, bottom)
        c.line(left, bottom - mark_len, left, bottom)
        c.line(right, bottom - mark_len, right, bottom)
        c.line(right, bottom, right + mark_len, bottom)
        c.line(left - mark_len, top, left, top)
        c.line(left, top, left, top + mark_len)
        c.line(right, top, right + mark_len, top)
        c.line(right, top, right, top + mark_len)
        c.setStrokeColorRGB(0, 0, 0)

        area_usada += (pos["ancho"] + 2 * sangrado) * (pos["alto"] + 2 * sangrado)

    image_cache.clear()
    agregar_marcas_registro(c, sheet_w_pt, sheet_h_pt)
    c.save()

    # Vista previa PNG opcional
    if preview_path:
        doc = fitz.open(output_path)
        pix = doc[0].get_pixmap(dpi=150, alpha=False)
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        pix.save(preview_path)
        doc.close()

    # Resumen HTML opcional
    if resumen_path:
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
        resumen_html = f"""
        <html><body>
        <h1>Resumen de montaje</h1>
        <p>Pliego: {ancho_pliego} x {alto_pliego} mm</p>
        <p>Diseños colocados: {colocados_total} de {total_disenos}</p>
        <p>Uso del pliego: {porcentaje:.1f}%</p>
        <p>{advertencias}</p>
        </body></html>
        """
        os.makedirs(os.path.dirname(resumen_path), exist_ok=True)
        with open(resumen_path, "w", encoding="utf-8") as f:
            f.write(resumen_html)

    return output_path
