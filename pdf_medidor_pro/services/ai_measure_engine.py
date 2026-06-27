"""Local AI-like measurement heuristics for PDF Medidor Pro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .geometry import round_mm
from .object_detector import count_objects, detect_object_near, detect_printed_area


def detect_measurement_near(
    image_path: str | Path,
    *,
    x_mm: float,
    y_mm: float,
    render_mm: dict[str, float],
    name: str = "Objeto detectado (IA)",
) -> dict[str, Any] | None:
    image_size = _image_size(image_path)
    x_px = _mm_to_px(x_mm, render_mm.get("ancho", 0), image_size["w"])
    y_px = _mm_to_px(y_mm, render_mm.get("alto", 0), image_size["h"])
    detection = detect_object_near(image_path, x_px=x_px, y_px=y_px)
    if detection is None:
        return None
    return _measurement_from_detection(detection, render_mm, name=name)


def detect_printed_measurement(
    image_path: str | Path,
    *,
    render_mm: dict[str, float],
    name: str = "Area impresa (IA)",
) -> dict[str, Any] | None:
    detection = detect_printed_area(image_path)
    if detection is None:
        return None
    return _measurement_from_detection(detection, render_mm, name=name)


def count_label_candidates(image_path: str | Path) -> dict[str, Any]:
    result = count_objects(image_path)
    return {
        "count": result["count"],
        "confidence": 0.62 if result["count"] else 0.25,
        "message": f"Se detectaron {result['count']} objetos candidatos.",
    }


def _measurement_from_detection(detection: dict[str, Any], render_mm: dict[str, float], *, name: str) -> dict[str, Any]:
    bbox = detection["bbox_px"]
    image = detection["image_px"]
    x_mm = _px_to_mm(bbox["x"], render_mm.get("ancho", 0), image["w"])
    y_mm = _px_to_mm(bbox["y"], render_mm.get("alto", 0), image["h"])
    w_mm = _px_to_mm(bbox["w"], render_mm.get("ancho", 0), image["w"])
    h_mm = _px_to_mm(bbox["h"], render_mm.get("alto", 0), image["h"])
    return {
        "tipo": "rectangulo",
        "origen": "ia",
        "nombre": name,
        "x_mm": round_mm(x_mm),
        "y_mm": round_mm(y_mm),
        "ancho_mm": round_mm(w_mm),
        "alto_mm": round_mm(h_mm),
        "area_mm2": round_mm(w_mm * h_mm),
        "perimetro_mm": round_mm((w_mm + h_mm) * 2),
        "confianza": round(float(detection.get("confidence", 0.0)), 3),
    }


def _image_size(image_path: str | Path) -> dict[str, int]:
    from PIL import Image

    with Image.open(image_path) as image:
        return {"w": image.width, "h": image.height}


def _px_to_mm(value_px: float, size_mm: float, size_px: float) -> float:
    return float(value_px) * float(size_mm or 0) / max(1.0, float(size_px or 1))


def _mm_to_px(value_mm: float, size_mm: float, size_px: float) -> float:
    return float(value_mm) * max(1.0, float(size_px or 1)) / max(1.0, float(size_mm or 1))
