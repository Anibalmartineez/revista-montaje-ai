# imposicion_offset_auto.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import math
import time
import uuid
from typing import Tuple, Dict, List

import fitz  # PyMuPDF
from pdf2image import convert_from_path

PT_PER_MM = 72.0 / 25.4


def mm_to_pt(mm: float) -> float:
    return mm * PT_PER_MM


def pt_to_mm(pt: float) -> float:
    return pt / PT_PER_MM


def _safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def detectar_tamano_final_corte(pdf_path: str) -> Tuple[float, float]:
    """
    Detección simplificada y robusta:
      1) Si la página tiene TrimBox -> usar TrimBox.
      2) Si no, usar MediaBox.
    Retorna (ancho_mm, alto_mm).
    Nota: Integra luego tu pipeline (dieline->cropmarks->visible) si ya existe.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    # PyMuPDF usa rect para MediaBox y puede exponer cajas; TrimBox si existe:
    rect = page.rect
    # Si existiera TrimBox usarla: (Compatibilidad simple)
    try:
        tb = page.trimbox
        if tb and tb.width > 0 and tb.height > 0:
            rect = tb
    except Exception:
        pass
    w_mm = pt_to_mm(rect.width)
    h_mm = pt_to_mm(rect.height)
    doc.close()
    return (w_mm, h_mm)


def _area(w: float, h: float) -> float:
    return w * h


def computar_capacidad_en_pliego(
    pieza_mm: Tuple[float, float],
    pliego_mm: Tuple[float, float],
    margen_mm: float,
    pinza_mm: float,
    gap_x_mm: float,
    gap_y_mm: float,
    permitir_rotar_90: bool,
    guia_lateral: str
) -> Dict:
    """
    Evalúa orientación 0° y 90° y devuelve el mejor layout por costo.
    Fórmulas:
        W_util = W - 2*margen - margen_guia
        H_util = H - pinza - margen
        cols = floor((W_util + gap_x) / (w + gap_x))
        filas = floor((H_util + gap_y) / (h + gap_y))
        repeticiones = filas * cols
        ocupacion = (repeticiones * w * h) / (W_util * H_util)
        costo = 0.6*(1/repeticiones) + 0.3*(1-ocupacion) + 0.1*penal
        start_x = margen + margen_guia + (W_util - (cols*w + (cols-1)*gap_x))/2
        start_y = pinza + (H_util - (filas*h + (filas-1)*gap_y))/2
    """
    W, H = pliego_mm
    best = None
    orientaciones = [(0, pieza_mm)]
    if permitir_rotar_90:
        orientaciones.append((90, (pieza_mm[1], pieza_mm[0])))

    # margen_guia: reservar margen extra en lado de guía
    guia_lateral = (guia_lateral or "izquierda").lower().strip()
    if guia_lateral not in ("izquierda", "derecha"):
        guia_lateral = "izquierda"

    for orient, (w, h) in orientaciones:
        # margen guía se reserva en el lado indicado
        margen_guia = margen_mm

        W_util = W - 2 * margen_mm - margen_guia
        H_util = H - pinza_mm - margen_mm

        if W_util <= 0 or H_util <= 0:
            continue

        cols = math.floor((W_util + gap_x_mm) / (w + gap_x_mm)) if (w + gap_x_mm) > 0 else 0
        filas = math.floor((H_util + gap_y_mm) / (h + gap_y_mm)) if (h + gap_y_mm) > 0 else 0

        if cols <= 0 or filas <= 0:
            continue

        rep = filas * cols
        if rep <= 0:
            continue

        area_util = max(1e-9, _area(W_util, H_util))
        ocupacion = (rep * _area(w, h)) / area_util

        # Penalizaciones simples
        pen = 0.0
        if cols < 2 or filas < 2:
            pen += 0.05

        costo = 0.6 * (1.0 / rep) + 0.3 * (1.0 - ocupacion) + 0.1 * pen

        total_w = cols * w + (cols - 1) * gap_x_mm
        total_h = filas * h + (filas - 1) * gap_y_mm
        start_x = margen_mm + margen_guia + (W_util - total_w) / 2.0
        start_y = pinza_mm + (H_util - total_h) / 2.0

        cand = {
            "orientacion": orient,
            "pliego_mm": [W, H],
            "grid": {"filas": filas, "columnas": cols},
            "repeticiones": rep,
            "ocupacion": ocupacion,
            "score": 1.0 / (1.0 + costo),  # score alto = mejor
            "offsets": {"x0": start_x, "y0": start_y},
            "gaps_mm": {"x": gap_x_mm, "y": gap_y_mm},
            "margen_mm": margen_mm,
            "pinza_mm": pinza_mm,
            "guia_lateral": guia_lateral,
            "pieza_mm": [w, h],
        }

        if best is None or cand["score"] > best["score"]:
            best = cand

    return best or {}


def _draw_registration_marks(page: fitz.Page, W_pt: float, H_pt: float) -> None:
    # Marcas simples en esquinas del pliego
    r = 6  # radio
    for (cx, cy) in [(10, 10), (W_pt - 10, 10), (10, H_pt - 10), (W_pt - 10, H_pt - 10)]:
        rect = fitz.Rect(cx - r, cy - r, cx + r, cy + r)
        page.draw_circle(rect, color=(0, 0, 0), fill=None, width=0.7)


def _draw_cut_marks(page: fitz.Page, x_pt: float, y_pt: float, w_pt: float, h_pt: float) -> None:
    # Marcas de corte en esquinas de cada pieza (ticks)
    tick = 8
    # Esquina inferior izquierda
    page.draw_line(fitz.Point(x_pt - tick, y_pt), fitz.Point(x_pt, y_pt))
    page.draw_line(fitz.Point(x_pt, y_pt - tick), fitz.Point(x_pt, y_pt))
    # inferior derecha
    page.draw_line(fitz.Point(x_pt + w_pt + tick, y_pt), fitz.Point(x_pt + w_pt, y_pt))
    page.draw_line(fitz.Point(x_pt + w_pt, y_pt - tick), fitz.Point(x_pt + w_pt, y_pt))
    # superior izquierda
    page.draw_line(fitz.Point(x_pt - tick, y_pt + h_pt), fitz.Point(x_pt, y_pt + h_pt))
    page.draw_line(fitz.Point(x_pt, y_pt + h_pt + tick), fitz.Point(x_pt, y_pt + h_pt))
    # superior derecha
    page.draw_line(fitz.Point(x_pt + w_pt + tick, y_pt + h_pt), fitz.Point(x_pt + w_pt, y_pt + h_pt))
    page.draw_line(fitz.Point(x_pt + w_pt, y_pt + h_pt + tick), fitz.Point(x_pt + w_pt, y_pt + h_pt))


def _draw_colorbar(page: fitz.Page, pinza_mm: float, barra_ancho_mm: float = 10, barra_alto_mm: float = 200):
    # Barra CMYK en margen de pinza (parte inferior)
    x0 = mm_to_pt(5)
    y0 = mm_to_pt(pinza_mm + 5)
    w = mm_to_pt(barra_ancho_mm)
    h = mm_to_pt(barra_alto_mm)
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)]  # C M Y K en RGB aprox
    for i, c in enumerate(colors):
        rect = fitz.Rect(x0 + i * (w + mm_to_pt(2)), y0, x0 + i * (w + mm_to_pt(2)) + w, y0 + h)
        page.draw_rect(rect, color=(0, 0, 0), fill=c, width=0.4)


def generar_pliego_pdf(
    pdf_pieza_path: str,
    pieza_mm: Tuple[float, float],
    layout: Dict,
    agregar_marcas: bool,
    agregar_colorbar: bool,
    salida_pdf_path: str
) -> None:
    src = fitz.open(pdf_pieza_path)
    dst = fitz.open()

    W_mm, H_mm = layout["pliego_mm"]
    W_pt, H_pt = mm_to_pt(W_mm), mm_to_pt(H_mm)
    page = dst.new_page(width=W_pt, height=H_pt)

    filas = layout["grid"]["filas"]
    cols = layout["grid"]["columnas"]
    start_x_mm = layout["offsets"]["x0"]
    start_y_mm = layout["offsets"]["y0"]
    gap_x_mm = layout["gaps_mm"]["x"]
    gap_y_mm = layout["gaps_mm"]["y"]
    orient = layout["orientacion"]

    # El tamaño colocado será exactamente pieza_mm (ya rotado si aplica)
    w_mm, h_mm = pieza_mm
    if orient == 90:
        w_mm, h_mm = pieza_mm[1], pieza_mm[0]

    w_pt, h_pt = mm_to_pt(w_mm), mm_to_pt(h_mm)

    src_page_index = 0
    for r in range(filas):
        for c in range(cols):
            x_mm = start_x_mm + c * (w_mm + gap_x_mm)
            y_mm = start_y_mm + r * (h_mm + gap_y_mm)
            rect = fitz.Rect(mm_to_pt(x_mm), mm_to_pt(y_mm), mm_to_pt(x_mm) + w_pt, mm_to_pt(y_mm) + h_pt)
            page.show_pdf_page(rect, src, src_page_index, rotate=orient)
            if agregar_marcas:
                _draw_cut_marks(page, rect.x0, rect.y0, w_pt, h_pt)

    if agregar_marcas:
        _draw_registration_marks(page, W_pt, H_pt)
    if agregar_colorbar:
        _draw_colorbar(page, layout["pinza_mm"])

    # Slug básico:
    slug = f"Imposición Offset Automática | {time.strftime('%Y-%m-%d %H:%M')} | {filas}x{cols} | Or: {orient}°"
    page.insert_text(fitz.Point(mm_to_pt(10), mm_to_pt(H_mm - 8)), slug, fontname="helv", fontsize=8, color=(0, 0, 0))

    dst.save(salida_pdf_path)
    dst.close()
    src.close()


def generar_preview_png(pliego_pdf_path: str, salida_png_path: str, dpi: int = 150) -> None:
    imgs = convert_from_path(pliego_pdf_path, dpi=dpi, first_page=1, last_page=1)
    if imgs:
        imgs[0].save(salida_png_path)


def resumen_json(
    pieza_mm: Tuple[float, float],
    layout: Dict,
    cantidad: int,
    salida_pdf: str,
    salida_png: str
) -> Dict:
    por_pliego = layout["repeticiones"]
    pliegos_necesarios = math.ceil(max(1, cantidad) / max(1, por_pliego))
    return {
        "pieza_mm": list(pieza_mm),
        "pliego_mm": layout["pliego_mm"],
        "orientacion_elegida": layout["orientacion"],
        "grid": layout["grid"],
        "repeticiones_por_pliego": por_pliego,
        "pliegos_necesarios": pliegos_necesarios,
        "ocupacion_porcentual": round(layout["ocupacion"] * 100.0, 2),
        "gaps_mm": layout["gaps_mm"],
        "margen_mm": layout["margen_mm"],
        "pinza_mm": layout["pinza_mm"],
        "guia_lateral": layout["guia_lateral"],
        "score": round(layout["score"], 4),
        "pliego_pdf": salida_pdf,
        "preview_png": salida_png,
    }


def imponer_pliego_offset_auto(
    pdf_path: str,
    cantidad: int,
    formatos_pliego_mm: List[List[float]],
    margen_mm: float,
    pinza_mm: float,
    guia_lateral: str,
    gap_x_mm: float,
    gap_y_mm: float,
    permitir_rotar_90: bool = True,
    agregar_marcas: bool = True,
    agregar_colorbar: bool = True,
    perfil_icc: str | None = None,
    salida_dir: str = "/tmp",
) -> Dict:
    """
    Orquesta todo y devuelve dict con ok, pliego_pdf, preview_png, resumen.
    """
    assert os.path.isfile(pdf_path), "PDF de entrada no encontrado"
    assert cantidad > 0, "Cantidad inválida"

    pieza_w_mm, pieza_h_mm = detectar_tamano_final_corte(pdf_path)

    best = None
    for W, H in formatos_pliego_mm:
        cand = computar_capacidad_en_pliego(
            pieza_mm=(pieza_w_mm, pieza_h_mm),
            pliego_mm=(W, H),
            margen_mm=margen_mm,
            pinza_mm=pinza_mm,
            gap_x_mm=gap_x_mm,
            gap_y_mm=gap_y_mm,
            permitir_rotar_90=permitir_rotar_90,
            guia_lateral=guia_lateral,
        )
        if cand and (best is None or cand["score"] > best["score"]):
            best = cand

    if not best:
        return {
            "ok": False,
            "error": "La pieza no cabe en ninguno de los formatos con los parámetros actuales.",
            "sugerencias": [
                "Reduce márgenes/gaps.",
                "Elige un formato de pliego mayor.",
                "Permite rotación 90° si estaba deshabilitada."
            ],
        }

    job_id = f"AGS-{uuid.uuid4().hex[:8]}"
    out_dir = os.path.join(salida_dir, job_id)
    _safe_mkdir(out_dir)

    salida_pdf = os.path.join(out_dir, f"{job_id}_pliego.pdf")
    salida_png = os.path.join(out_dir, f"{job_id}_preview.png")

    generar_pliego_pdf(
        pdf_pieza_path=pdf_path,
        pieza_mm=(pieza_w_mm, pieza_h_mm),
        layout=best,
        agregar_marcas=agregar_marcas,
        agregar_colorbar=agregar_colorbar,
        salida_pdf_path=salida_pdf,
    )
    generar_preview_png(salida_pdf, salida_png, dpi=150)
    info = resumen_json((pieza_w_mm, pieza_h_mm), best, cantidad, salida_pdf, salida_png)
    return {"ok": True, "pliego_pdf": salida_pdf, "preview_png": salida_png, "resumen": info}
