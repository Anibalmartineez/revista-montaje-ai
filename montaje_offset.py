import os
import io
from typing import Dict, List, Tuple
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


MM_TO_PT = 2.83465  # milímetros a puntos (300 dpi)

SHEET_FORMATS: Dict[str, Tuple[float, float]] = {
    "700x1000": (700.0, 1000.0),
    "640x880": (640.0, 880.0),
}


def mm_to_pt(valor: float) -> float:
    return valor * MM_TO_PT


def _pdf_a_imagen_con_sangrado(path: str, sangrado_mm: float) -> ImageReader:
    doc = fitz.open(path)
    page = doc.load_page(0)
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


def calcular_distribucion(sheet_w: float, sheet_h: float,
                          job_w: float, job_h: float,
                          margen_sup: float, margen_inf: float,
                          margen_izq: float, margen_der: float,
                          espaciado_h: float, espaciado_v: float,
                          sangrado: float) -> Tuple[int, int, int]:
    """Calcula cuántas repeticiones entran considerando márgenes y espacios."""
    total_w = job_w + 2 * sangrado
    total_h = job_h + 2 * sangrado
    cols = max(int((sheet_w - margen_izq - margen_der + espaciado_h) // (total_w + espaciado_h)), 0)
    rows = max(int((sheet_h - margen_sup - margen_inf + espaciado_v) // (total_h + espaciado_v)), 0)
    return cols, rows, cols * rows


def dibujar_formas(c: canvas.Canvas, imagenes: List[ImageReader],
                   cols: int, rows: int,
                   job_w_pt: float, job_h_pt: float, sangrado_pt: float,
                   margen_izq_pt: float, margen_inf_pt: float,
                   espaciado_h_pt: float, espaciado_v_pt: float) -> None:
    idx = 0
    total_w = job_w_pt + 2 * sangrado_pt
    total_h = job_h_pt + 2 * sangrado_pt
    for r in range(rows):
        for c_idx in range(cols):
            img = imagenes[idx % len(imagenes)]
            x = margen_izq_pt + c_idx * (total_w + espaciado_h_pt)
            y = margen_inf_pt + r * (total_h + espaciado_v_pt)
            c.drawImage(img, x, y, width=total_w, height=total_h)
            idx += 1


def agregar_marcas_corte(c: canvas.Canvas, cols: int, rows: int,
                         job_w_pt: float, job_h_pt: float, sangrado_pt: float,
                         margen_izq_pt: float, margen_inf_pt: float,
                         espaciado_h_pt: float, espaciado_v_pt: float) -> None:
    """Dibuja marcas de corte reales fuera del área de cada trabajo."""
    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(0.3)
    mark_len = mm_to_pt(3)
    total_w = job_w_pt + 2 * sangrado_pt
    total_h = job_h_pt + 2 * sangrado_pt
    for r in range(rows):
        for c_idx in range(cols):
            x = margen_izq_pt + c_idx * (total_w + espaciado_h_pt)
            y = margen_inf_pt + r * (total_h + espaciado_v_pt)
            left = x + sangrado_pt
            bottom = y + sangrado_pt
            right = left + job_w_pt
            top = bottom + job_h_pt
            # Esquinas inferiores
            c.line(left - mark_len, bottom, left, bottom)
            c.line(left, bottom - mark_len, left, bottom)
            c.line(right, bottom - mark_len, right, bottom)
            c.line(right, bottom, right + mark_len, bottom)
            # Esquinas superiores
            c.line(left - mark_len, top, left, top)
            c.line(left, top, left, top + mark_len)
            c.line(right, top, right + mark_len, top)
            c.line(right, top, right, top + mark_len)
    c.setStrokeColorRGB(0, 0, 0)


def agregar_marcas_registro(c: canvas.Canvas, sheet_w_pt: float, sheet_h_pt: float) -> None:
    mark_len = mm_to_pt(5)
    offset = mm_to_pt(5)
    x = sheet_w_pt / 2
    c.setLineWidth(0.3)
    for y in (offset, sheet_h_pt - offset):
        c.line(x - mark_len, y, x + mark_len, y)
        c.line(x, y - mark_len, x, y + mark_len)
        c.circle(x, y, mm_to_pt(1), stroke=1, fill=0)


def generar_dorso(c: canvas.Canvas, imagenes: List[ImageReader],
                  cols: int, rows: int,
                  job_w_pt: float, job_h_pt: float, sangrado_pt: float,
                  margen_izq_pt: float, margen_inf_pt: float,
                  espaciado_h_pt: float, espaciado_v_pt: float,
                  sheet_w_pt: float, sheet_h_pt: float,
                  modo: str) -> None:
    if modo == "retiracion":
        c.saveState()
        c.translate(sheet_w_pt, 0)
        c.scale(-1, 1)
        dibujar_formas(c, imagenes, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                       margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
        agregar_marcas_corte(c, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                             margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
        c.restoreState()
    else:  # tirada
        dibujar_formas(c, imagenes, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                       margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
        agregar_marcas_corte(c, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                             margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
    agregar_marcas_registro(c, sheet_w_pt, sheet_h_pt)


def generar_vista_previa(pdf_path: str, preview_path: str) -> None:
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=150)
    pix.save(preview_path)
    doc.close()


def generar_reporte_tecnico(info: Dict[str, str], output_path: str) -> None:
    lines = ["<html><body><h1>Reporte Técnico</h1><ul>"]
    for k, v in info.items():
        lines.append(f"<li><b>{k}:</b> {v}</li>")
    lines.append("</ul></body></html>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def montar_pliego_offset(file_paths: List[str], formato_pliego: str,
                         trabajo_size: Tuple[float, float],
                         modo_dorso: str = None,
                         margen_sup: float = 10.0,
                         margen_inf: float = 10.0,
                         margen_izq: float = 10.0,
                         margen_der: float = 10.0,
                         espaciado_h: float = 5.0,
                         espaciado_v: float = 5.0,
                         sangrado: float = 0.0,
                         output_dir: str = "output") -> Tuple[str, str, str]:
    os.makedirs(output_dir, exist_ok=True)

    sheet = SHEET_FORMATS.get(formato_pliego)
    if sheet is None:
        try:
            sheet = tuple(map(float, formato_pliego.lower().split("x")))
        except Exception:
            sheet = (700.0, 1000.0)
    sheet_w, sheet_h = sheet

    job_w, job_h = trabajo_size
    cols, rows, total = calcular_distribucion(sheet_w, sheet_h, job_w, job_h,
                                              margen_sup, margen_inf,
                                              margen_izq, margen_der,
                                              espaciado_h, espaciado_v, sangrado)

    imagenes = [_pdf_a_imagen_con_sangrado(p, sangrado) for p in file_paths]

    sheet_w_pt = mm_to_pt(sheet_w)
    sheet_h_pt = mm_to_pt(sheet_h)
    job_w_pt = mm_to_pt(job_w)
    job_h_pt = mm_to_pt(job_h)
    sangrado_pt = mm_to_pt(sangrado)
    margen_sup_pt = mm_to_pt(margen_sup)
    margen_inf_pt = mm_to_pt(margen_inf)
    margen_izq_pt = mm_to_pt(margen_izq)
    margen_der_pt = mm_to_pt(margen_der)
    espaciado_h_pt = mm_to_pt(espaciado_h)
    espaciado_v_pt = mm_to_pt(espaciado_v)

    pdf_path = os.path.join(output_dir, "pliego_offset.pdf")
    preview_path = os.path.join(output_dir, "preview.png")
    reporte_path = os.path.join(output_dir, "reporte_tecnico.html")

    c = canvas.Canvas(pdf_path, pagesize=(sheet_w_pt, sheet_h_pt))
    dibujar_formas(c, imagenes, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                   margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
    agregar_marcas_corte(c, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                         margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt)
    agregar_marcas_registro(c, sheet_w_pt, sheet_h_pt)

    if modo_dorso in ("tirada", "retiracion"):
        c.showPage()
        generar_dorso(c, imagenes, cols, rows, job_w_pt, job_h_pt, sangrado_pt,
                      margen_izq_pt, margen_inf_pt, espaciado_h_pt, espaciado_v_pt,
                      sheet_w_pt, sheet_h_pt, modo_dorso)

    c.save()

    generar_vista_previa(pdf_path, preview_path)

    info = {
        "Medida del pliego": f"{sheet_w}x{sheet_h} mm",
        "Medida del trabajo": f"{job_w}x{job_h} mm",
        "Copias por pliego (filas x columnas)": f"{rows} x {cols}",
        "Márgenes": f"sup {margen_sup} mm, inf {margen_inf} mm, izq {margen_izq} mm, der {margen_der} mm",
        "Espacios entre formas": f"h {espaciado_h} mm, v {espaciado_v} mm",
        "Modo": modo_dorso if modo_dorso else "Solo frente",
        "Archivos utilizados": ", ".join(os.path.basename(p) for p in file_paths),
        "Fecha de generación": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    generar_reporte_tecnico(info, reporte_path)

    return pdf_path, preview_path, reporte_path

