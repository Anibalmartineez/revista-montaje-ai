import fitz
from typing import List

def rect_iou(r1: fitz.Rect, r2: fitz.Rect) -> float:
    inter = r1 & r2
    if inter.width <= 0 or inter.height <= 0:
        return 0.0
    union = r1 | r2
    inter_area = inter.width * inter.height
    union_area = union.width * union.height
    return inter_area / union_area if union_area else 0.0

def intersect_rects(rects: List[fitz.Rect]):
    if not rects:
        return None
    inter = rects[0]
    for r in rects[1:]:
        inter = inter & r
    if inter.width <= 0 or inter.height <= 0:
        return None
    return inter

def weighted_rect(rects: List[fitz.Rect], weights: List[float]):
    total = sum(weights)
    if total == 0 or not rects:
        return None
    x0 = sum(r.x0 * w for r, w in zip(rects, weights)) / total
    y0 = sum(r.y0 * w for r, w in zip(rects, weights)) / total
    x1 = sum(r.x1 * w for r, w in zip(rects, weights)) / total
    y1 = sum(r.y1 * w for r, w in zip(rects, weights)) / total
    return fitz.Rect(x0, y0, x1, y1)

def center_rect(rect: fitz.Rect, page_w: float, page_h: float) -> fitz.Rect:
    left = rect.x0
    right = page_w - rect.x1
    top = rect.y0
    bottom = page_h - rect.y1
    dx = (right - left) / 2
    dy = (bottom - top) / 2
    return rect + (dx, dy, dx, dy)
