import io
from typing import List, Dict, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

MM_TO_PT = 2.83465  # milímetros a puntos


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


def calcular_posiciones(
    disenos: List[Dict[str, float]],
    ancho_pliego: float,
    alto_pliego: float,
    margen: float = 10,
    separacion: float = 5,
    sangrado: float = 0,
    centrar: bool = False,
    alinear_filas: bool = False,
) -> List[Dict[str, float]]:
    """Calcula posiciones de cada diseño evitando solapamientos.

    Cuando ``alinear_filas`` es ``True`` se construye una grilla uniforme
    utilizando el ancho y alto máximos de los diseños para determinar el tamaño
    de cada celda. Si ``centrar`` es ``True`` el bloque resultante se centra en
    el pliego tanto horizontal como verticalmente.
    """

    posiciones: List[Dict[str, float]] = []

    if alinear_filas and disenos:
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
            posiciones.append(
                {
                    "archivo": diseno["archivo"],
                    "x": x,
                    "y": y,
                    "ancho": diseno["ancho"],
                    "alto": diseno["alto"],
                }
            )
    else:
        # Comenzamos desde la esquina superior izquierda
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

            posiciones.append(
                {
                    "archivo": diseno["archivo"],
                    "x": x_cursor,
                    # Convertimos a coordenadas de origen inferior izquierdo
                    "y": y_cursor - alto_total,
                    "ancho": diseno["ancho"],
                    "alto": diseno["alto"],
                }
            )

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


def montar_pliego_offset_inteligente(
    diseños: List[Tuple[str, int]],
    ancho_pliego: float,
    alto_pliego: float,
    margen: float = 10,
    separacion: float = 4,
    sangrado: float = 3,
    ordenar_tamano: bool = False,
    alinear_filas: bool = False,
    centrar: bool = False,
    output_path: str = "output/pliego_offset_inteligente.pdf",
) -> str:
    """Genera un PDF montado acomodando diseños de distintos tamaños."""
    disenos: List[Dict[str, float]] = []
    for path, cantidad in diseños:
        ancho, alto = obtener_dimensiones_pdf(path)
        for _ in range(cantidad):
            disenos.append({"archivo": path, "ancho": ancho, "alto": alto})

    if ordenar_tamano:
        disenos.sort(key=lambda d: d["ancho"], reverse=True)
    else:
        disenos.sort(key=lambda d: d["ancho"] * d["alto"], reverse=True)
    posiciones = calcular_posiciones(
        disenos,
        ancho_pliego,
        alto_pliego,
        margen=margen,
        separacion=separacion,
        sangrado=sangrado,
        centrar=centrar,
        alinear_filas=alinear_filas,
    )

    sheet_w_pt = mm_to_pt(ancho_pliego)
    sheet_h_pt = mm_to_pt(alto_pliego)
    c = canvas.Canvas(output_path, pagesize=(sheet_w_pt, sheet_h_pt))

    for pos in posiciones:
        img = _pdf_a_imagen_con_sangrado(pos["archivo"], sangrado)
        total_w_pt = mm_to_pt(pos["ancho"] + 2 * sangrado)
        total_h_pt = mm_to_pt(pos["alto"] + 2 * sangrado)
        x_pt = mm_to_pt(pos["x"])
        y_pt = mm_to_pt(pos["y"])
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

    agregar_marcas_registro(c, sheet_w_pt, sheet_h_pt)
    c.save()
    return output_path
