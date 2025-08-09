import base64
import io
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image, ImageDraw

try:
    from ia_sugerencias import chat_completion
except Exception:  # pragma: no cover - fallback when API not configured
    def chat_completion(*args, **kwargs):
        return ""

PT_PER_MM = 72 / 25.4


def pt_to_mm(v: float) -> float:
    return round(v / PT_PER_MM, 2)


def mm_to_pt(v: float) -> float:
    return v * PT_PER_MM


def clamp_rect(rect: fitz.Rect, page_w: float, page_h: float) -> fitz.Rect:
    return fitz.Rect(
        max(0, rect.x0),
        max(0, rect.y0),
        min(page_w, rect.x1),
        min(page_h, rect.y1),
    )


def rect_size_mm(rect: fitz.Rect) -> Dict[str, float]:
    return {"w": pt_to_mm(rect.width), "h": pt_to_mm(rect.height)}


def get_pdf_boxes(page: fitz.Page) -> Dict[str, fitz.Rect]:
    return {
        "mediabox": getattr(page, "mediabox", page.rect),
        "cropbox": page.cropbox or page.rect,
        "trimbox": page.trimbox,
        "bleedbox": page.bleedbox,
    }


def detect_dieline_vector(doc: fitz.Document, page: fitz.Page):
    rects: List[fitz.Rect] = []
    page_area = page.rect.get_area()
    for d in page.get_drawings():
        if d.get("fill"):
            continue
        if d.get("width", 0) > 1.0:
            continue
        stroke = d.get("stroke") or d.get("color")
        if not stroke:
            continue
        bbox = d.get("bbox") or d.get("rect")
        if not bbox:
            continue
        r = fitz.Rect(bbox)
        if r.width < 10 or r.height < 10:
            continue
        if r.get_area() / page_area < 0.3:
            continue
        rects.append(r)
    if not rects:
        return None, [], 0.0, {}
    largest = max(rects, key=lambda r: r.get_area())
    return largest, rects, 0.85, {"source": "DieLine"}


def detect_cropmarks_vector(page: fitz.Page, page_w: float, page_h: float):
    vert_x: List[float] = []
    horiz_y: List[float] = []
    for d in page.get_drawings():
        stroke = d.get("stroke") or d.get("color")
        if not stroke:
            continue
        if d.get("width", 0) > 1.0:
            continue
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
            elif len(item) == 3 and item[0] == 'l':
                p0, p1 = item[1], item[2]
                x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
            else:
                continue
            if abs(x0 - x1) < 0.5:
                length = abs(y1 - y0)
                if 3 <= pt_to_mm(length) <= 15:
                    vert_x.append((x0 + x1) / 2)
            elif abs(y0 - y1) < 0.5:
                length = abs(x1 - x0)
                if 3 <= pt_to_mm(length) <= 15:
                    horiz_y.append((y0 + y1) / 2)
    if len(vert_x) >= 2 and len(horiz_y) >= 2:
        rect = fitz.Rect(min(vert_x), min(horiz_y), max(vert_x), max(horiz_y))
        rect = clamp_rect(rect, page_w, page_h)
        return rect, [], 0.6, {"source": "CropMarks"}
    return None, [], 0.0, {}


def detect_trim_raster(page: fitz.Page):
    zoom = 300 / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    coords = cv2.findNonZero(edges)
    if coords is None:
        return None, [], 0.0, {}
    x, y, w, h = cv2.boundingRect(coords)
    x0, y0 = x / zoom, y / zoom
    x1, y1 = (x + w) / zoom, (y + h) / zoom
    rect = fitz.Rect(x0, y0, x1, y1)
    return rect, [], 0.4, {"source": "RasterBBox"}


def compute_final_area(page: fitz.Page):
    page_w, page_h = page.rect.width, page.rect.height
    boxes = get_pdf_boxes(page)
    notes: List[str] = []
    components: List[fitz.Rect] = []

    tb = boxes.get("trimbox")
    if tb and tb != page.rect and tb.width > 0 and tb.height > 0:
        tb = clamp_rect(tb, page_w, page_h)
        return tb, 0.9, {"source": "TrimBox"}, components, notes

    rect, comps, conf, info = detect_dieline_vector(page.parent, page)
    if rect:
        components = comps
        if len(comps) > 1:
            union = comps[0]
            for r in comps[1:]:
                union = union | r
            rect = union
            notes.append("Se detectaron varios troqueles.")
        rect = clamp_rect(rect, page_w, page_h)
        return rect, conf, info, components, notes

    rect, comps, conf, info = detect_cropmarks_vector(page, page_w, page_h)
    if rect:
        rect = clamp_rect(rect, page_w, page_h)
        return rect, conf, info, components, notes

    rect, comps, conf, info = detect_trim_raster(page)
    if rect:
        components = comps
        rect = clamp_rect(rect, page_w, page_h)
        return rect, conf, info, components, notes

    cb = boxes.get("cropbox")
    if cb and (cb.width != page_w or cb.height != page_h):
        cb = clamp_rect(cb, page_w, page_h)
        return cb, 0.3, {"source": "CropBox"}, components, notes

    mb = boxes.get("mediabox") or page.rect
    mb = clamp_rect(mb, page_w, page_h)
    return mb, 0.2, {"source": "MediaBox"}, components, notes


def measure_bleed(page: fitz.Page, final_rect: fitz.Rect):
    content_rect, _, _, _ = detect_trim_raster(page)
    if not content_rect:
        return {"top": 0.0, "right": 0.0, "bottom": 0.0, "left": 0.0}
    top = max(0, final_rect.y0 - content_rect.y0)
    bottom = max(0, content_rect.y1 - final_rect.y1)
    left = max(0, final_rect.x0 - content_rect.x0)
    right = max(0, content_rect.x1 - final_rect.x1)
    return {
        "top": round(pt_to_mm(top), 1),
        "right": round(pt_to_mm(right), 1),
        "bottom": round(pt_to_mm(bottom), 1),
        "left": round(pt_to_mm(left), 1),
    }


def diagnostico_offset_pro(pdf_path: str, page_index: int = 0):
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    page_w, page_h = page.rect.width, page.rect.height
    page_size_mm = {"w": pt_to_mm(page_w), "h": pt_to_mm(page_h)}

    final_rect, confidence, info, components, notes = compute_final_area(page)
    bleed = measure_bleed(page, final_rect)

    if confidence < 0.6:
        notes.append("Verificar recorte (confianza media/baja).")
    if any(v < 3 for v in bleed.values()):
        notes.append("Alerta: sangrado menor a 3 mm en alguno de los lados.")

    final_size_mm = rect_size_mm(final_rect)
    final_origin_mm = {"x": pt_to_mm(final_rect.x0), "y": pt_to_mm(final_rect.y0)}

    components_mm = [
        (pt_to_mm(r.x0), pt_to_mm(r.y0), pt_to_mm(r.x1), pt_to_mm(r.y1))
        for r in components
    ]

    out_dict = {
        "page_size_mm": page_size_mm,
        "final_size_mm": final_size_mm,
        "final_origin_mm": final_origin_mm,
        "detected_by": info.get("source", ""),
        "confidence": confidence,
        "bleed_mm": bleed,
        "components_count": len(components_mm) if components_mm else 1,
        "final_components": components_mm,
        "notes": notes,
    }

    zoom = 110 / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, pix.width - 1, pix.height - 1], outline="black", width=2)
    draw.rectangle(
        [
            final_rect.x0 * zoom,
            final_rect.y0 * zoom,
            final_rect.x1 * zoom,
            final_rect.y1 * zoom,
        ],
        outline="red",
        width=3,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    preview_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    ai_summary = ""
    try:
        prompt = (
            f"Tamaño final: {final_size_mm['w']} x {final_size_mm['h']} mm. "
            f"Detectado por: {info.get('source')}. "
            f"Confianza: {confidence}. Sangrado: {bleed}. "
            f"Notas: {', '.join(notes)}"
        )
        ai_summary = chat_completion(prompt)
    except Exception:
        pass
    out_dict["ai_summary"] = ai_summary

    return out_dict, preview_b64


def diagnosticar_pdf(path: str) -> str:
    resultado, _ = diagnostico_offset_pro(path)
    return resultado.get("ai_summary", "")


__all__ = ["diagnostico_offset_pro", "diagnosticar_pdf"]
