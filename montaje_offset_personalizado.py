"""Módulo para el modo de montaje offset PRO totalmente personalizado.

Este modo es independiente del montaje estándar y permite controlar cada
detalle del pliego: repeticiones exactas por archivo, márgenes, separación y
alineación personalizada. Si no es posible colocar todas las repeticiones en un
único pliego se genera un ``ValueError`` y no se crea ningún PDF.
"""

import math
import os
import tempfile
from typing import Dict, List, Tuple

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from montaje_offset_inteligente import (
    mm_to_pt,
    detectar_sangrado_pdf,
    obtener_dimensiones_pdf,
    _pdf_a_imagen_con_sangrado,
    draw_cutmarks_around_form_reportlab,
    _bbox_add,
    recortar_pdf_a_bbox,
)


def _rotar_pdf_si_corresponde(path: str) -> None:
    """Rota 90° un PDF sobre sí mismo si es necesario."""

    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        try:
            page.rotate_clockwise(90)
        except Exception:
            page.rotate(90)
        writer.add_page(page)
    with open(path, "wb") as out_f:
        writer.write(out_f)


def montar_pliego_offset_personalizado(
    specs: List[Dict], pro_config: Dict
) -> Tuple[str, List[Dict]]:
    """Genera un pliego en modo PRO totalmente personalizado.

    Parameters
    ----------
    specs: list[dict]
        Lista de especificaciones por archivo. Cada dict acepta las claves
        ``file``, ``filename``, ``reps``, ``rotate``, ``bleed_mm``, ``cutmarks``
        y ``align``.
    pro_config: dict
        Configuración global del pliego.

    Returns
    -------
    tuple(str, list[dict])
        Ruta al PDF generado y un resumen de montado.
    """

    # --- Lectura de configuración global ---
    pliego_w = float(pro_config.get("pliego_w_mm", 0))
    pliego_h = float(pro_config.get("pliego_h_mm", 0))
    margen_izq = float(pro_config.get("margen_izq_mm", 0))
    margen_der = float(pro_config.get("margen_der_mm", margen_izq))
    margen_sup = float(pro_config.get("margen_sup_mm", 0))
    margen_inf = float(pro_config.get("margen_inf_mm", margen_sup))
    sep_h = float(pro_config.get("sep_h_mm", 0))
    sep_v = float(pro_config.get("sep_v_mm", 0))
    export_area_util = bool(pro_config.get("export_area_util", False))
    preview = bool(pro_config.get("preview", False))

    pliego_w_pt = mm_to_pt(pliego_w)
    pliego_h_pt = mm_to_pt(pliego_h)

    available_w = pliego_w - margen_izq - margen_der
    current_y = margen_sup

    output_path = os.path.join("output", "pliego_offset_pro.pdf")
    c = canvas.Canvas(output_path, pagesize=(pliego_w_pt, pliego_h_pt))
    bbox = [None, None, None, None]

    colores_preview = [
        colors.red,
        colors.blue,
        colors.green,
        colors.magenta,
        colors.orange,
        colors.purple,
        colors.cyan,
        colors.brown,
    ]

    resumen: List[Dict] = []
    tmp_paths: List[str] = []

    for idx, spec in enumerate(specs):
        file_storage = spec.get("file")
        reps = int(spec.get("reps") or 0)
        if reps <= 0:
            raise ValueError("Repeticiones inválidas en especificación")

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(tmp_fd, "wb") as tmp:
            tmp.write(file_storage.read())

        if spec.get("rotate"):
            _rotar_pdf_si_corresponde(tmp_path)

        bleed_mm = spec.get("bleed_mm")
        usar_trimbox = True
        if bleed_mm is None:
            bleed_mm = detectar_sangrado_pdf(tmp_path)
            usar_trimbox = False

        bleed_pt = mm_to_pt(bleed_mm)

        # Dimensiones y rasterización según el sangrado
        if usar_trimbox:
            w_trim_mm, h_trim_mm = obtener_dimensiones_pdf(tmp_path, usar_trimbox=True)
            w_total_mm = w_trim_mm + 2 * bleed_mm
            h_total_mm = h_trim_mm + 2 * bleed_mm
            img = _pdf_a_imagen_con_sangrado(
                tmp_path, sangrado_mm=bleed_mm, usar_trimbox=True
            )
        else:
            w_total_mm, h_total_mm = obtener_dimensiones_pdf(tmp_path)
            w_trim_mm, h_trim_mm = obtener_dimensiones_pdf(tmp_path, usar_trimbox=True)
            img = _pdf_a_imagen_con_sangrado(
                tmp_path, sangrado_mm=0, usar_trimbox=False
            )

        w_total_pt = mm_to_pt(w_total_mm)
        h_total_pt = mm_to_pt(h_total_mm)
        w_trim_pt = mm_to_pt(w_trim_mm)
        h_trim_pt = mm_to_pt(h_trim_mm)

        max_cols = math.floor((available_w + sep_h) / (w_total_mm + sep_h))
        if max_cols <= 0:
            raise ValueError("No caben todas las repeticiones en el pliego personalizado")
        rows_needed = math.ceil(reps / max_cols)
        total_height = rows_needed * h_total_mm + (rows_needed - 1) * sep_v
        if current_y + total_height > pliego_h - margen_inf:
            raise ValueError("No caben todas las repeticiones en el pliego personalizado")

        posiciones: List[Tuple[float, float]] = []  # en mm (top-left)
        restante = reps
        y_fila = current_y
        for r in range(rows_needed):
            cols_en_fila = min(restante, max_cols)
            fila_ancho = cols_en_fila * w_total_mm + (cols_en_fila - 1) * sep_h
            align = spec.get("align", "center")
            if align == "left":
                x_inicio = margen_izq
            elif align == "right":
                x_inicio = pliego_w - margen_der - fila_ancho
            else:  # center
                x_inicio = margen_izq + (available_w - fila_ancho) / 2

            x_col = x_inicio
            for _ in range(cols_en_fila):
                posiciones.append((x_col, y_fila))
                x_col += w_total_mm + sep_h

            restante -= cols_en_fila
            if r < rows_needed - 1:
                y_fila += h_total_mm + sep_v
            else:
                y_fila += h_total_mm

        current_y = y_fila + sep_v

        color = colores_preview[idx % len(colores_preview)]
        for x_mm, y_mm in posiciones:
            x_pt = mm_to_pt(x_mm)
            # Convertir coordenadas: de sistema top-left a bottom-left
            y_pt = pliego_h_pt - mm_to_pt(y_mm) - h_total_pt
            c.drawImage(img, x_pt, y_pt, width=w_total_pt, height=h_total_pt)

            if preview:
                c.setStrokeColor(color)
                c.setLineWidth(1)
                c.rect(
                    x_pt + bleed_pt,
                    y_pt + bleed_pt,
                    w_trim_pt,
                    h_trim_pt,
                    stroke=1,
                    fill=0,
                )

            if spec.get("cutmarks") and bleed_mm > 0:
                draw_cutmarks_around_form_reportlab(
                    c,
                    x_pt + bleed_pt,
                    y_pt + bleed_pt,
                    w_trim_pt,
                    h_trim_pt,
                    bleed_mm,
                )

            _bbox_add(bbox, x_pt, y_pt, x_pt + w_total_pt, y_pt + h_total_pt)

        resumen.append(
            {
                "archivo": spec.get("filename")
                or getattr(file_storage, "filename", f"file_{idx+1}.pdf"),
                "reps_pedidas": reps,
                "reps_montadas": len(posiciones),
                "pliego": f"{pliego_w}x{pliego_h} mm",
            }
        )

        tmp_paths.append(tmp_path)

    c.save()

    for p in tmp_paths:
        try:
            os.remove(p)
        except OSError:
            pass

    if export_area_util and bbox[0] is not None:
        recortar_pdf_a_bbox(output_path, output_path, [bbox])

    return output_path, resumen

