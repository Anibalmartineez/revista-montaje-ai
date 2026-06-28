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
    mediciones: list[dict[str, Any]] | None = None,
    origen_medida_final: str = "manual",
    confianza: str = "alta",
) -> dict[str, Any]:
    return {
        "archivo": archivo,
        "pagina": int(pagina or 1),
        "medidas_auto": _normalize_auto_boxes(medidas_auto),
        "medidas_manual": normalize_manual_measurements(medidas_manual),
        "calibracion": normalize_calibration(calibracion),
        "origen_medida_final": _origin(origen_medida_final),
        "confianza": confianza or "alta",
        "mediciones": _normalize_measurements(mediciones),
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


def _normalize_measurements(mediciones: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not isinstance(mediciones, list):
        return []
    return [_normalize_measurement(item) for item in mediciones if isinstance(item, dict)]


def _normalize_measurement(item: dict[str, Any]) -> dict[str, Any]:
    measurement = {
        "id": str(item.get("id") or ""),
        "tipo": str(item.get("tipo") or "rectangulo"),
        "origen": _origin(str(item.get("origen") or "manual")),
        "nombre": str(item.get("nombre") or "Medicion"),
        "visible": bool(item.get("visible", True)),
        "color": str(item.get("color") or "#0f766e"),
        "stroke_width": _number(item.get("stroke_width")) or 1.0,
        "pagina": _positive_int(item.get("pagina")),
    }
    for key in ("ancho_mm", "alto_mm", "x_mm", "y_mm", "area_mm2", "perimetro_mm", "angulo_deg"):
        measurement[key] = _signed_number(item.get(key))
    measurement["confianza"] = _confidence(item.get("confianza"))
    if isinstance(item.get("a"), dict):
        measurement["a"] = {"x_mm": _signed_number(item["a"].get("x_mm")), "y_mm": _signed_number(item["a"].get("y_mm"))}
    if isinstance(item.get("b"), dict):
        measurement["b"] = {"x_mm": _signed_number(item["b"].get("x_mm")), "y_mm": _signed_number(item["b"].get("y_mm"))}
    return measurement


def _signed_number(value: Any) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


def _positive_int(value: Any) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return 1
    return numeric if numeric > 0 else 1


def _confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, numeric)), 3)


def _origin(value: Any) -> str:
    normalized = str(value or "manual").strip().lower()
    return normalized if normalized in {"manual", "auto"} else "manual"
