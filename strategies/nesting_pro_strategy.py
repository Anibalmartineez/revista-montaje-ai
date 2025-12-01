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


class NestingProStrategy(BaseMontajeStrategy):
    def calcular(
        self,
        disenos: List[Tuple[str, int]],
        config,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        ancho_pliego, alto_pliego, kwargs = build_call_args(config)
        layout = _build_nesting_layout(disenos, config)
        nesting_result = compute_nesting(layout)
        posiciones = _slots_to_posiciones(nesting_result.slots, float(config.sangrado or 0.0))

        kwargs["estrategia"] = "manual"
        kwargs["posiciones_override"] = posiciones
        return montar_pliego_offset_inteligente(disenos, ancho_pliego, alto_pliego, **kwargs)
