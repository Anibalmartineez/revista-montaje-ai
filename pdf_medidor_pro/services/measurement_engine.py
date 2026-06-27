"""Manual measurement normalization for PDF Medidor Pro."""

from __future__ import annotations

from typing import Any

from .geometry import round_mm


def normalize_manual_measurements(payload: dict[str, Any] | None) -> dict[str, float]:
    payload = payload or {}
    width = _positive_number(payload.get("ancho_final_mm"))
    height = _positive_number(payload.get("alto_final_mm"))
    return {
        "ancho_final_mm": round_mm(width),
        "alto_final_mm": round_mm(height),
    }


def _positive_number(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if numeric > 0 else 0.0
