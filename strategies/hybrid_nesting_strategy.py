from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engines.nesting_pro_engine import compute_nesting
from montaje_offset_inteligente import obtener_dimensiones_pdf, montar_pliego_offset_inteligente

from .base import BaseMontajeStrategy
from .common import build_call_args


def _build_nesting_layout(disenos: List[Tuple[str, int]], config) -> Dict:
    ancho_pliego, alto_pliego, _ = build_call_args(config)
    designs: List[Dict[str, Any]] = []
    bleed_default = float(config.sangrado or 0.0)
    allow_rotation = bool(config.permitir_rotacion)

    for idx, (ruta_pdf, copias) in enumerate(disenos):
        width_mm, height_mm = obtener_dimensiones_pdf(ruta_pdf, usar_trimbox=config.usar_trimbox)
        designs.append(
            {
                "ref": str(idx),
                "width_mm": width_mm,
                "height_mm": height_mm,
                "bleed_mm": bleed_default,
                "allow_rotation": allow_rotation,
                "forms_per_plate": max(1, int(copias)),
            }
        )

    return {
        "sheet_mm": [float(ancho_pliego), float(alto_pliego)],
        "margins_mm": [
            float(config.margen_izquierdo),
            float(config.margen_derecho),
            float(config.margen_superior),
            float(config.margen_inferior),
        ],
        "gap_default_mm": float(config.separacion or 0.0),
        "designs": designs,
    }


def _usable_area(config) -> Tuple[float, float, float, float]:
    sheet_w, sheet_h = config.tamano_pliego
    usable_w = float(sheet_w) - float(config.margen_izquierdo) - float(config.margen_derecho)
    usable_h = float(sheet_h) - float(config.margen_superior) - float(config.margen_inferior)
    return usable_w, usable_h, float(config.margen_izquierdo), float(config.margen_inferior)


def _repeat_pattern(base_slots: List[Dict[str, Any]], bbox: Tuple[float, float, float, float], config) -> List[Dict[str, Any]]:
    if not base_slots:
        return []

    usable_w, usable_h, left, bottom = _usable_area(config)
    if usable_w <= 0 or usable_h <= 0:
        return []

    min_x, min_y, max_x, max_y = bbox
    block_w = max(0.0, max_x - min_x)
    block_h = max(0.0, max_y - min_y)
    if block_w <= 0 or block_h <= 0:
        return base_slots

    gap = float(config.separacion or 0.0)
    slots: List[Dict[str, Any]] = []
    y_offset = bottom
    while y_offset + block_h <= bottom + usable_h + 1e-6:
        x_offset = left
        while x_offset + block_w <= left + usable_w + 1e-6:
            for slot in base_slots:
                slots.append(
                    {
                        **slot,
                        "x_mm": x_offset + (slot["x_mm"] - min_x),
                        "y_mm": y_offset + (slot["y_mm"] - min_y),
                    }
                )
            x_offset += block_w + gap
        y_offset += block_h + gap
    return slots


def _slots_to_posiciones(slots: List[Dict[str, Any]], bleed_default: float) -> List[Dict[str, Any]]:
    posiciones: List[Dict[str, Any]] = []
    for slot in slots:
        try:
            ref_idx = int(slot.get("design_ref"))
        except (TypeError, ValueError):
            continue

        bleed_mm = float(slot.get("bleed_mm", bleed_default) or 0.0)
        w_trim = float(slot.get("w_mm", 0.0)) - 2 * bleed_mm
        h_trim = float(slot.get("h_mm", 0.0)) - 2 * bleed_mm
        posiciones.append(
            {
                "file_idx": ref_idx,
                "x_mm": float(slot.get("x_mm", 0.0)),
                "y_mm": float(slot.get("y_mm", 0.0)),
                "w_mm": w_trim if w_trim > 0 else float(slot.get("w_mm", 0.0)),
                "h_mm": h_trim if h_trim > 0 else float(slot.get("h_mm", 0.0)),
                "rot_deg": int(slot.get("rotation_deg", 0)) % 360,
                "bleed_mm": bleed_mm,
            }
        )
    return posiciones


class HybridNestingStrategy(BaseMontajeStrategy):
    def calcular(
        self,
        disenos: List[Tuple[str, int]],
        config,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        ancho_pliego, alto_pliego, kwargs = build_call_args(config)
        layout = _build_nesting_layout(disenos, config)
        nesting_result = compute_nesting(layout)
        repeated_slots = _repeat_pattern(nesting_result.slots, nesting_result.bbox, config)
        posiciones = _slots_to_posiciones(repeated_slots, float(config.sangrado or 0.0))

        kwargs["estrategia"] = "manual"
        kwargs["posiciones_override"] = posiciones
        return montar_pliego_offset_inteligente(disenos, ancho_pliego, alto_pliego, **kwargs)
