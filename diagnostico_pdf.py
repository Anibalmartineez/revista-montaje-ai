import io, gc, base64
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from utils_img import dpi_for_preview, dpi_for_raster_ops

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


# ------------------------------------------------------------
# NUEVO: Detección robusta de troquel (dieline)
# ------------------------------------------------------------
def detect_dieline_bbox_advanced(page: fitz.Page, page_w: float, page_h: float):
    """
    Heurística para troquel: trazos finos, sin relleno, color rojo/magenta (no obligatorio),
    a veces dashed. Se unifican todos los bboxes relevantes.
    """
    try:
        drawings = page.get_drawings()
    except Exception:
        return None, [], 0.0, {}

    dieline_rects = []
    MAX_STROKE_PT = 1.2
    MIN_PATH_SEGMENTS = 4

    def likely_dieline_color(rgb):
        if not rgb or len(rgb) < 3:
            return False
        r, g, b = rgb[:3]
        return (r > 0.7 and g < 0.35 and b < 0.35) or (r > 0.6 and b > 0.6 and g < 0.35)

    for d in drawings:
        if not d.get("stroke"):
            continue
        width = float(d.get("width") or 0.0)
        if width > MAX_STROKE_PT:
            continue
        color = d.get("color", None)
        dashes = d.get("dashes", None)
        items = d.get("items", [])
        if not items or len(items) < MIN_PATH_SEGMENTS:
            continue
        xs, ys = [], []
        for it in items:
            if len(it) == 4:
                x0, y0, x1, y1 = it
                xs += [x0, x1]; ys += [y0, y1]
            elif len(it) == 3 and it[0] == 'l':
                p0, p1 = it[1], it[2]
                xs += [p0.x, p1.x]; ys += [p0.y, p1.y]
        if not xs:
            continue
        r = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
        if r.width < 10 or r.height < 10:
            continue
        if likely_dieline_color(color) or dashes is not None or width <= 0.6:
            dieline_rects.append(r)

    if not dieline_rects:
        return None, [], 0.0, {}

    union = dieline_rects[0]
    for rr in dieline_rects[1:]:
        union = union | rr
    union = clamp_rect(union, page_w, page_h)
    return union, dieline_rects, 0.85, {"source": "DielineBBox"}


def rect_size_mm(rect: fitz.Rect) -> Dict[str, float]:
    return {"w": pt_to_mm(rect.width), "h": pt_to_mm(rect.height)}


def get_pdf_boxes(page: fitz.Page) -> Dict[str, fitz.Rect]:
    return {
        "mediabox": getattr(page, "mediabox", page.rect),
        "cropbox": page.cropbox or page.rect,
        "trimbox": page.trimbox,
        "bleedbox": page.bleedbox,
    }


def detect_cropmarks_vector(page: fitz.Page, page_w: float, page_h: float):
    """Líneas finas cerca del borde que forman pares verticales/horizontales; devuelve rectángulo interior."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None, [], 0.0, {}

    vert_x, horiz_y, marks = [], [], []
    MAX_STROKE_PT = 0.8
    MAX_DIST_EDGE_PT = mm_to_pt(15)
    MIN_LEN_MM, MAX_LEN_MM = 3.0, 15.0

    for d in drawings:
        if not d.get("stroke") or (d.get("width", 0) or 0) > MAX_STROKE_PT:
            continue
        for item in d.get("items", []):
            if len(item) == 4:
                x0, y0, x1, y1 = item
            elif len(item) == 3 and item[0] == 'l':
                p0, p1 = item[1], item[2]
                x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
            else:
                continue
            is_vert = abs(x0 - x1) < 0.5
            is_horz = abs(y0 - y1) < 0.5
            if not (is_vert or is_horz):
                continue
            length_pt = abs((y1 - y0) if is_vert else (x1 - x0))
            length_mm = pt_to_mm(length_pt)
            if not (MIN_LEN_MM <= length_mm <= MAX_LEN_MM):
                continue
            near_edge = (
                min(x0, x1) < MAX_DIST_EDGE_PT or page_w - max(x0, x1) < MAX_DIST_EDGE_PT or
                min(y0, y1) < MAX_DIST_EDGE_PT or page_h - max(y0, y1) < MAX_DIST_EDGE_PT
            )
            if not near_edge:
                continue
            marks.append((x0, y0, x1, y1))
            if is_vert:
                vert_x.append((x0 + x1) / 2)
            if is_horz:
                horiz_y.append((y0 + y1) / 2)

    if len(vert_x) >= 2 and len(horiz_y) >= 2:
        rect = fitz.Rect(min(vert_x), min(horiz_y), max(vert_x), max(horiz_y))
        rect = clamp_rect(rect, page_w, page_h)
        return rect, marks, 0.75, {"source": "CropMarks"}
    return None, [], 0.0, {}


def raster_visible_bbox(page: fitz.Page, page_mm):
    """Fallback visual: renderiza, elimina líneas finas/ruido y toma bbox de masa visible."""
    dpi = dpi_for_raster_ops(page_mm)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    import numpy as np, cv2
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    arr = arr.reshape(pix.height, pix.width, pix.n)

    if pix.n == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    binv = cv2.threshold(blur, 245, 255, cv2.THRESH_BINARY_INV)[1]
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(binv, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    coords = cv2.findNonZero(mask)
    if coords is None:
        del arr
        pix = None
        fitz.TOOLS.store_shrink(1)
        gc.collect()
        return None, [], 0.0, {}

    x, y, w, h = cv2.boundingRect(coords)
    scale = 72 / dpi
    x0, y0 = x * scale, y * scale
    x1, y1 = (x + w) * scale, (y + h) * scale
    rect = fitz.Rect(x0, y0, x1, y1)

    del arr
    pix = None
    fitz.TOOLS.store_shrink(1)
    gc.collect()
    return rect, [], 0.55, {"source": "VisibleRaster"}


def compute_final_area(page: fitz.Page):
    page_w, page_h = page.rect.width, page.rect.height
    boxes = get_pdf_boxes(page)
    notes: List[str] = []
    components: List[fitz.Rect] = []

    tb = boxes.get("trimbox")
    if tb and tb != page.rect and tb.width > 0 and tb.height > 0:
        tb = clamp_rect(tb, page_w, page_h)
        return tb, 0.9, {"source": "TrimBox"}, components, notes

    rect, comps, conf, info = detect_dieline_bbox_advanced(page, page_w, page_h)
    if rect:
        components = comps
        if len(comps) > 1:
            notes.append("Se detectaron varios troqueles.")
        rect = clamp_rect(rect, page_w, page_h)
        return rect, conf, info, components, notes

    rect, comps, conf, info = detect_cropmarks_vector(page, page_w, page_h)
    if rect:
        rect = clamp_rect(rect, page_w, page_h)
        return rect, conf, info, components, notes

    rect, comps, conf, info = raster_visible_bbox(page, (pt_to_mm(page_w), pt_to_mm(page_h)))
    if rect:
        components = comps
        rect = clamp_rect(rect, page_w, page_h)
        notes.append("área útil estimada desde contenido visible")
        return rect, conf, info, components, notes

    cb = boxes.get("cropbox")
    if cb and (cb.width != page_w or cb.height != page_h):
        cb = clamp_rect(cb, page_w, page_h)
        return cb, 0.3, {"source": "CropBox"}, components, notes

    mb = boxes.get("mediabox") or page.rect
    mb = clamp_rect(mb, page_w, page_h)
    return mb, 0.2, {"source": "MediaBox"}, components, notes


def measure_bleed(page: fitz.Page, final_rect: fitz.Rect):
    content_rect, _, _, _ = raster_visible_bbox(page, (pt_to_mm(page.rect.width), pt_to_mm(page.rect.height)))
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


def generar_preview_jpg(page, final_rect_pt=None, page_mm=(210, 297), draw_overlay=True):
    # 1) DPI dinámico para preview
    dpi = dpi_for_preview(page_mm)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # 2) PIL Image
    im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(im)

    # 3) Overlays (opcional)
    if draw_overlay and final_rect_pt:
        def pt2px(v):
            return int(round(v * (dpi / 72)))

        x0, y0, x1, y1 = final_rect_pt
        draw.rectangle([pt2px(x0), pt2px(y0), pt2px(x1), pt2px(y1)], outline="red", width=3)
        draw.rectangle([0, 0, pix.width - 1, pix.height - 1], outline="black", width=1)

    # 4) Exportar JPEG optimizado (reduce RAM y base64)
    bio = io.BytesIO()
    im.save(bio, format="JPEG", quality=70, optimize=True, progressive=True)
    preview_bytes = bio.getvalue()

    # 5) Liberar memoria agresivo
    im.close()
    del im
    bio.close()
    pix = None
    del pix
    fitz.TOOLS.store_shrink(1)
    gc.collect()

    return preview_bytes


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
    preview_bytes = generar_preview_jpg(
        page,
        (final_rect.x0, final_rect.y0, final_rect.x1, final_rect.y1),
        (page_size_mm["w"], page_size_mm["h"]),
    )

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
    doc.close()

    return out_dict, preview_bytes


def diagnosticar_pdf(path: str) -> str:
    resultado, _ = diagnostico_offset_pro(path)
    return resultado.get("ai_summary", "")


__all__ = ["diagnostico_offset_pro", "diagnosticar_pdf"]
