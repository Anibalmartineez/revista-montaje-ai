"""Geometry helpers for PDF point, millimeter, and pixel measurements."""

from __future__ import annotations

from math import hypot
from typing import Any

PT_PER_MM = 72.0 / 25.4


def pt_to_mm(value_pt: float) -> float:
    return float(value_pt) / PT_PER_MM


def mm_to_pt(value_mm: float) -> float:
    return float(value_mm) * PT_PER_MM


def round_mm(value: float) -> float:
    return round(float(value), 3)


def rect_size_mm(rect: Any | None) -> dict[str, float]:
    if rect is None:
        return {"ancho": 0.0, "alto": 0.0}
    width = float(getattr(rect, "width", 0) or 0)
    height = float(getattr(rect, "height", 0) or 0)
    if width <= 0 or height <= 0:
        return {"ancho": 0.0, "alto": 0.0}
    return {"ancho": round_mm(pt_to_mm(width)), "alto": round_mm(pt_to_mm(height))}


def distance_components_mm(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    mm_per_px_x: float,
    mm_per_px_y: float,
    scale_factor: float = 1.0,
) -> dict[str, float]:
    dx = abs(float(bx) - float(ax)) * float(mm_per_px_x) * float(scale_factor)
    dy = abs(float(by) - float(ay)) * float(mm_per_px_y) * float(scale_factor)
    return {
        "horizontal_mm": round_mm(dx),
        "vertical_mm": round_mm(dy),
        "diagonal_mm": round_mm(hypot(dx, dy)),
    }
