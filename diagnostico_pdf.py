import io, gc, base64
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from utils_img import dpi_for_preview, dpi_for_raster_ops
from utils_geom import rect_iou, intersect_rects, weighted_rect, center_rect

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
    MAX_STROKE_PT = 2.0
    MIN_PATH_SEGMENTS = 2

    def likely_dieline_color(rgb):
        """Return True if color matches typical dieline hues (red/magenta, cyan or dark gray/black)."""
        if not rgb or len(rgb) < 3:
            return False
        r, g, b = rgb[:3]
        # Red or magenta: red channel dominant
        if (r > 0.7 and g < 0.35 and b < 0.35) or (r > 0.6 and b > 0.6 and g < 0.35):
            return True
        # Cyan: blue dominant with some green
        if b > 0.6 and g > 0.6 and r < 0.35:
            return True
        # Black or dark gray: all channels low and similar
        if max(r, g, b) < 0.25 and max(abs(r - g), abs(r - b), abs(g - b)) < 0.1:
            return True
        return False

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
        "artbox": getattr(page, "artbox", None),
    }


def detect_cropmarks_vector(page: fitz.Page, page_w: float, page_h: float):
    """Líneas finas cerca del borde que forman pares verticales/horizontales; devuelve rectángulo interior."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None, [], 0.0, {}

    vert_x, horiz_y, marks = [], [], []
    MAX_STROKE_PT = 1.5
    MAX_DIST_EDGE_PT = min(page_w, page_h) * 0.10
    MIN_LEN_MM, MAX_LEN_MM = 2.0, 25.0

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
    _, binv = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
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


def detect_rectangular_contours(page: fitz.Page):
    """Busca contornos rectangulares cerrados en los dibujos vectoriales."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None, [], 0.0, {}

    rects = []
    for d in drawings:
        items = d.get("items", [])
        lines = []
        for it in items:
            if len(it) == 4:
                x0, y0, x1, y1 = it
            elif len(it) == 3 and it[0] == 'l':
                p0, p1 = it[1], it[2]
                x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
            else:
                continue
            lines.append((x0, y0, x1, y1))
        if len(lines) < 4:
            continue
        xs = [p for ln in lines for p in (ln[0], ln[2])]
        ys = [p for ln in lines for p in (ln[1], ln[3])]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        w, h = maxx - minx, maxy - miny
        if w < 10 or h < 10:
            continue
        # check lines near rectangle sides
        eps = 1.0
        sides = {'left': 0, 'right': 0, 'top': 0, 'bottom': 0}
        for x0, y0, x1, y1 in lines:
            if abs(x0 - minx) < eps and abs(x1 - minx) < eps:
                sides['left'] += 1
            elif abs(x0 - maxx) < eps and abs(x1 - maxx) < eps:
                sides['right'] += 1
            elif abs(y0 - miny) < eps and abs(y1 - miny) < eps:
                sides['top'] += 1
            elif abs(y0 - maxy) < eps and abs(y1 - maxy) < eps:
                sides['bottom'] += 1
        if all(v > 0 for v in sides.values()):
            rects.append(fitz.Rect(minx, miny, maxx, maxy))

    if not rects:
        return None, [], 0.0, {}
    rect = max(rects, key=lambda r: r.width * r.height)
    return rect, rects, 0.6, {"source": "RectContours"}


def compute_final_area(page: fitz.Page):
    page_w, page_h = page.rect.width, page.rect.height
    boxes = get_pdf_boxes(page)
    notes: List[str] = []
    components: List[fitz.Rect] = []

    art = boxes.get("artbox")
    if art and art.width > 0 and art.height > 0 and art != page.rect:
        art = clamp_rect(art, page_w, page_h)
        notes.append("Usando ArtBox del PDF.")
        return art, 0.95, {"source": "ArtBox"}, components, notes

    tb = boxes.get("trimbox")
    if tb and tb != page.rect and tb.width > 0 and tb.height > 0:
        tb = clamp_rect(tb, page_w, page_h)
        return tb, 0.9, {"source": "TrimBox"}, components, notes

    dieline_rect, dieline_comps, dieline_conf, dieline_info = detect_dieline_bbox_advanced(page, page_w, page_h)
    crop_rect, crop_comps, crop_conf, crop_info = detect_cropmarks_vector(page, page_w, page_h)
    raster_rect, raster_comps, raster_conf, raster_info = raster_visible_bbox(page, (pt_to_mm(page_w), pt_to_mm(page_h)))
    contour_rect, contour_comps, contour_conf, contour_info = detect_rectangular_contours(page)

    results = []
    if dieline_rect:
        results.append(("dieline", dieline_rect, dieline_conf, dieline_comps, dieline_info))
    if crop_rect:
        results.append(("crop", crop_rect, crop_conf, crop_comps, crop_info))
    if raster_rect:
        results.append(("raster", raster_rect, raster_conf, raster_comps, raster_info))
    if contour_rect:
        results.append(("contour", contour_rect, contour_conf, contour_comps, contour_info))

    final_rect = None
    confidence = 0.0
    info: Dict[str, str] = {}

    if dieline_rect and crop_rect:
        overlap = rect_iou(dieline_rect, crop_rect)
        if overlap >= 0.9:
            final_rect = dieline_rect & crop_rect
            confidence = (dieline_conf + crop_conf) / 2 + 0.05
            info = {"source": "Dieline+Crop"}
            components = dieline_comps + crop_comps
            notes.append("Coincidencia alta entre troquel y marcas de corte.")

    if not final_rect and results:
        rects = [r for _, r, _, _, _ in results]
        confs = [c for _, _, c, _, _ in results]
        inter = intersect_rects(rects)
        if inter:
            final_rect = inter
            confidence = sum(confs) / len(confs)
            info = {"source": "+".join([n for n, *_ in results])}
            notes.append("Rectángulo por intersección de métodos.")
        else:
            final_rect = weighted_rect(rects, confs)
            confidence = sum(confs) / len(confs) - 0.1
            info = {"source": "+".join([n for n, *_ in results])}
            notes.append("Rectángulo por media ponderada de métodos.")
        for _, _, _, comps, _ in results:
            components.extend(comps)

    if not final_rect:
        cb = boxes.get("cropbox")
        if cb and (cb.width != page_w or cb.height != page_h):
            cb = clamp_rect(cb, page_w, page_h)
            return cb, 0.3, {"source": "CropBox"}, components, notes
        mb = boxes.get("mediabox") or page.rect
        mb = clamp_rect(mb, page_w, page_h)
        return mb, 0.2, {"source": "MediaBox"}, components, notes

    final_rect = clamp_rect(final_rect, page_w, page_h)

    size_mm = rect_size_mm(final_rect)
    STD_SIZES = {"A4": (210.0, 297.0), "Carta": (215.9, 279.4)}
    for name, (sw, sh) in STD_SIZES.items():
        if abs(size_mm["w"] - sw) <= 2 and abs(size_mm["h"] - sh) <= 2:
            center_x = (final_rect.x0 + final_rect.x1) / 2
            center_y = (final_rect.y0 + final_rect.y1) / 2
            final_rect = fitz.Rect(
                center_x - mm_to_pt(sw) / 2,
                center_y - mm_to_pt(sh) / 2,
                center_x + mm_to_pt(sw) / 2,
                center_y + mm_to_pt(sh) / 2,
            )
            size_mm = {"w": sw, "h": sh}
            notes.append(f"Normalizado al tamaño estándar {name}.")
            break

    left = final_rect.x0
    right = page_w - final_rect.x1
    top = final_rect.y0
    bottom = page_h - final_rect.y1
    if abs(pt_to_mm(left - right)) > 2 or abs(pt_to_mm(top - bottom)) > 2:
        final_rect = center_rect(final_rect, page_w, page_h)
        notes.append("Rectángulo centrado debido a asimetría detectada.")

    return final_rect, confidence, info, components, notes


def measure_bleed(page: fitz.Page, final_rect: fitz.Rect):
    page_w, page_h = page.rect.width, page.rect.height
    page_mm = (pt_to_mm(page_w), pt_to_mm(page_h))
    boxes = get_pdf_boxes(page)
    bleedbox = boxes.get("bleedbox")
    crop_rect, marks, _, _ = detect_cropmarks_vector(page, page_w, page_h)
    raster_rect, _, _, _ = raster_visible_bbox(page, page_mm)

    def mark_pos(side: str):
        if not marks:
            return None
        cand = None
        for x0, y0, x1, y1 in marks:
            is_vert = abs(x0 - x1) < 0.5
            is_horz = abs(y0 - y1) < 0.5
            if side == "left" and is_vert and max(x0, x1) <= final_rect.x0:
                cand = max(cand or -float("inf"), max(x0, x1))
            elif side == "right" and is_vert and min(x0, x1) >= final_rect.x1:
                cand = min(cand or float("inf"), min(x0, x1))
            elif side == "top" and is_horz and max(y0, y1) <= final_rect.y0:
                cand = max(cand or -float("inf"), max(y0, y1))
            elif side == "bottom" and is_horz and min(y0, y1) >= final_rect.y1:
                cand = min(cand or float("inf"), min(y0, y1))
        return cand

    bleed = {}
    for side in ["top", "right", "bottom", "left"]:
        if bleedbox:
            if side == "top":
                val = max(0, final_rect.y0 - bleedbox.y0)
            elif side == "bottom":
                val = max(0, bleedbox.y1 - final_rect.y1)
            elif side == "left":
                val = max(0, final_rect.x0 - bleedbox.x0)
            else:
                val = max(0, bleedbox.x1 - final_rect.x1)
        else:
            mp = mark_pos(side)
            if mp is not None:
                if side == "top":
                    val = max(0, final_rect.y0 - mp)
                elif side == "bottom":
                    val = max(0, mp - final_rect.y1)
                elif side == "left":
                    val = max(0, final_rect.x0 - mp)
                else:
                    val = max(0, mp - final_rect.x1)
            elif raster_rect:
                if side == "top":
                    val = max(0, final_rect.y0 - raster_rect.y0)
                elif side == "bottom":
                    val = max(0, raster_rect.y1 - final_rect.y1)
                elif side == "left":
                    val = max(0, final_rect.x0 - raster_rect.x0)
                else:
                    val = max(0, raster_rect.x1 - final_rect.x1)
            else:
                val = 0
        bleed[side] = round(pt_to_mm(val), 1)

    return bleed


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
    for side, val in bleed.items():
        if val == 0:
            notes.append(f"Sin sangrado en lado {side}.")
        elif val < 3:
            notes.append(f"Sangrado menor a 3 mm en lado {side}.")

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
