"""Snap helpers for PDF Medidor Pro."""

from __future__ import annotations

from math import hypot
from typing import Any

DEFAULT_THRESHOLD_MM = 2.0
STRICT_THRESHOLD_MM = 0.75


def snap_point(
    point: dict[str, Any],
    measurements: list[dict[str, Any]] | None,
    *,
    enabled: bool = True,
    strict: bool = False,
) -> dict[str, Any]:
    """Snap a point in page-mm coordinates to the closest eligible candidate."""

    normalized = {"x_mm": _number(point.get("x_mm")), "y_mm": _number(point.get("y_mm"))}
    if not enabled:
        return {"snapped": False, "point": normalized, "candidate": None, "distance_mm": None}

    threshold = STRICT_THRESHOLD_MM if strict else DEFAULT_THRESHOLD_MM
    best: dict[str, Any] | None = None
    for candidate in snap_candidates(measurements or []):
        distance = hypot(candidate["x_mm"] - normalized["x_mm"], candidate["y_mm"] - normalized["y_mm"])
        if distance <= threshold and (best is None or distance < best["distance_mm"]):
            best = {"candidate": candidate, "distance_mm": round(distance, 3)}

    if best is None:
        return {"snapped": False, "point": normalized, "candidate": None, "distance_mm": None}

    return {
        "snapped": True,
        "point": {"x_mm": best["candidate"]["x_mm"], "y_mm": best["candidate"]["y_mm"]},
        "candidate": best["candidate"],
        "distance_mm": best["distance_mm"],
    }


def snap_candidates(measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for measurement in measurements:
        kind = measurement.get("tipo") or measurement.get("type")
        mid = str(measurement.get("id") or "")
        if kind == "linea":
            _line_candidates(candidates, measurement, mid)
        elif kind == "rectangulo":
            _rectangle_candidates(candidates, measurement, mid)
    return candidates


def _line_candidates(candidates: list[dict[str, Any]], measurement: dict[str, Any], mid: str) -> None:
    for label, key in (("inicio", "a"), ("fin", "b")):
        point = measurement.get(key) or {}
        candidates.append(
            {
                "source_id": mid,
                "kind": f"linea_{label}",
                "x_mm": _number(point.get("x_mm")),
                "y_mm": _number(point.get("y_mm")),
            }
        )


def _rectangle_candidates(candidates: list[dict[str, Any]], measurement: dict[str, Any], mid: str) -> None:
    x = _number(measurement.get("x_mm"))
    y = _number(measurement.get("y_mm"))
    w = _number(measurement.get("ancho_mm") or measurement.get("w_mm"))
    h = _number(measurement.get("alto_mm") or measurement.get("h_mm"))
    points = {
        "esquina_sup_izq": (x, y),
        "esquina_sup_der": (x + w, y),
        "esquina_inf_izq": (x, y + h),
        "esquina_inf_der": (x + w, y + h),
        "centro": (x + w / 2, y + h / 2),
        "borde_sup": (x + w / 2, y),
        "borde_inf": (x + w / 2, y + h),
        "borde_izq": (x, y + h / 2),
        "borde_der": (x + w, y + h / 2),
    }
    for kind, (px, py) in points.items():
        candidates.append({"source_id": mid, "kind": kind, "x_mm": round(px, 3), "y_mm": round(py, 3)})


def _number(value: Any) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0
