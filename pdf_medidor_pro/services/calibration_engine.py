"""Calibration helpers for manual PDF measurements."""

from __future__ import annotations

from .geometry import round_mm


def calculate_scale_factor(measured_mm: float, real_mm: float) -> float:
    measured = float(measured_mm)
    real = float(real_mm)
    if measured <= 0:
        raise ValueError("La medicion seleccionada debe ser mayor que cero.")
    if real <= 0:
        raise ValueError("La medida real debe ser mayor que cero.")
    return round(real / measured, 6)


def normalize_calibration(payload: dict | None) -> dict[str, float | bool]:
    payload = payload or {}
    active = bool(payload.get("activa", False))
    factor = float(payload.get("factor_escala", 1) or 1)
    if factor <= 0:
        factor = 1.0
        active = False
    return {"activa": active, "factor_escala": round(factor, 6)}


def apply_scale(value_mm: float, factor: float) -> float:
    return round_mm(float(value_mm) * float(factor))
