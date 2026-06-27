"""Export contract builder for PDF Medidor Pro."""

from __future__ import annotations

from typing import Any

from .calibration_engine import normalize_calibration
from .measurement_engine import normalize_manual_measurements

AUTO_BOX_KEYS = (
    "mediabox_mm",
    "cropbox_mm",
    "trimbox_mm",
    "bleedbox_mm",
    "artbox_mm",
)


def build_export_payload(
    *,
    archivo: str,
    pagina: int,
    medidas_auto: dict[str, Any] | None,
    medidas_manual: dict[str, Any] | None,
    calibracion: dict[str, Any] | None,
    origen_medida_final: str = "manual",
    confianza: str = "alta",
) -> dict[str, Any]:
    return {
        "archivo": archivo,
        "pagina": int(pagina or 1),
        "medidas_auto": _normalize_auto_boxes(medidas_auto),
        "medidas_manual": normalize_manual_measurements(medidas_manual),
        "calibracion": normalize_calibration(calibracion),
        "origen_medida_final": origen_medida_final or "manual",
        "confianza": confianza or "alta",
    }


def _normalize_auto_boxes(medidas_auto: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    medidas_auto = medidas_auto or {}
    return {key: _box(medidas_auto.get(key)) for key in AUTO_BOX_KEYS}


def _box(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {"ancho": 0.0, "alto": 0.0}
    return {
        "ancho": _number(value.get("ancho")),
        "alto": _number(value.get("alto")),
    }


def _number(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(numeric, 3) if numeric > 0 else 0.0
