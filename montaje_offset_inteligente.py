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
    espacio: float = 5,
    sangrado: float = 0,
    centrar_vertical: bool = False,
) -> List[Dict[str, float]]:
    """Calcula posiciones de cada diseño evitando solapamientos.

    Los diseños se colocan en filas y columnas comenzando desde la parte
    superior izquierda del pliego. Cuando un diseño no entra horizontalmente
    se pasa a la siguiente fila. Si ``centrar_vertical`` es ``True`` se
    distribuyen las filas para que el espacio libre inferior y superior sea el
    mismo.
    """

    posiciones: List[Dict[str, float]] = []

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
            y_cursor -= fila_max_altura + espacio
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

        x_cursor += ancho_total + espacio
        fila_max_altura = max(fila_max_altura, alto_total)

    if centrar_vertical and posiciones:
        # Calculamos el espacio libre y desplazamos las filas al centro
        min_y = min(p["y"] for p in posiciones)
        used_height = (alto_pliego - margen) - min_y
        espacio_libre = (alto_pliego - 2 * margen) - used_height
        if espacio_libre > 0:
            desplazamiento = espacio_libre / 2
            for p in posiciones:
                p["y"] -= desplazamiento

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
    file_paths: List[str],
    ancho_pliego: float,
    alto_pliego: float,
    margen: float = 10,
    espacio: float = 5,
    sangrado: float = 3,
    output_path: str = "output/pliego_offset_inteligente.pdf",
) -> str:
    """Genera un PDF montado acomodando diseños de distintos tamaños."""
    disenos: List[Dict[str, float]] = []
    for path in file_paths:
        ancho, alto = obtener_dimensiones_pdf(path)
        disenos.append({"archivo": path, "ancho": ancho, "alto": alto})

    disenos.sort(key=lambda d: d["ancho"] * d["alto"], reverse=True)
    posiciones = calcular_posiciones(
        disenos,
        ancho_pliego,
        alto_pliego,
        margen=margen,
        espacio=espacio,
        sangrado=sangrado,
        centrar_vertical=True,
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
