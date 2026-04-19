from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple


EPSILON = 1e-6


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _active_face(layout: Dict[str, Any]) -> str:
    return str(layout.get("active_face") or "front")


def _slot_face(slot: Dict[str, Any]) -> str:
    return str(slot.get("face") or "front")


def _sheet_bounds(layout: Dict[str, Any]) -> Dict[str, float]:
    sheet = layout.get("sheet_mm") or [0, 0]
    margins = layout.get("margins_mm") or [0, 0, 0, 0]
    sheet_w = _to_float(sheet[0] if len(sheet) > 0 else 0)
    sheet_h = _to_float(sheet[1] if len(sheet) > 1 else 0)
    left = _to_float(margins[0] if len(margins) > 0 else 0)
    right = _to_float(margins[1] if len(margins) > 1 else 0)
    top = _to_float(margins[2] if len(margins) > 2 else 0)
    bottom = _to_float(margins[3] if len(margins) > 3 else 0)
    usable_w = max(0.0, sheet_w - left - right)
    usable_h = max(0.0, sheet_h - top - bottom)
    return {
        "left": left,
        "bottom": bottom,
        "right": left + usable_w,
        "top": bottom + usable_h,
        "width": usable_w,
        "height": usable_h,
        "area_mm2": usable_w * usable_h,
    }


def _slot_box(slot: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    x = _to_float(slot.get("x_mm"))
    y = _to_float(slot.get("y_mm"))
    w = _to_float(slot.get("w_mm"))
    h = _to_float(slot.get("h_mm"))
    if w <= EPSILON or h <= EPSILON:
        return None
    return x, y, x + w, y + h


def _target_slots(layout: Dict[str, Any], include_locked: bool = True) -> List[Dict[str, Any]]:
    face = _active_face(layout)
    slots = layout.get("slots") or []
    if not isinstance(slots, list):
        return []
    return [
        slot
        for slot in slots
        if isinstance(slot, dict)
        and _slot_face(slot) == face
        and (include_locked or not bool(slot.get("locked")))
    ]


def _bbox(slots: Iterable[Dict[str, Any]]) -> Optional[Tuple[float, float, float, float]]:
    boxes = [_slot_box(slot) for slot in slots]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def analizar_layout(layout: Dict[str, Any]) -> Dict[str, Any]:
    slots = _target_slots(layout)
    usable = _sheet_bounds(layout)
    used_area = sum(
        max(0.0, _to_float(slot.get("w_mm"))) * max(0.0, _to_float(slot.get("h_mm")))
        for slot in slots
    )
    free_area = max(0.0, usable["area_mm2"] - used_area)
    usage_pct = (used_area / usable["area_mm2"] * 100.0) if usable["area_mm2"] > EPSILON else 0.0
    bbox = _bbox(slots)
    dead_spaces: List[Dict[str, Any]] = []

    if bbox:
        min_x, min_y, max_x, max_y = bbox
        gaps = [
            ("izquierda", usable["left"], min_x, usable["height"]),
            ("derecha", max_x, usable["right"], usable["height"]),
            ("abajo", usable["bottom"], min_y, max(0.0, max_x - min_x)),
            ("arriba", max_y, usable["top"], max(0.0, max_x - min_x)),
        ]
        for name, start, end, span in gaps:
            gap = max(0.0, end - start)
            if gap > EPSILON:
                dead_spaces.append(
                    {
                        "zona": name,
                        "ancho_mm": round(gap, 3),
                        "area_mm2": round(gap * max(0.0, span), 3),
                    }
                )

    return {
        "face": _active_face(layout),
        "slot_count": len(slots),
        "area_usada_mm2": round(used_area, 3),
        "area_libre_mm2": round(free_area, 3),
        "aprovechamiento_pct": round(usage_pct, 2),
        "bbox": (
            {
                "x_min_mm": round(bbox[0], 3),
                "y_min_mm": round(bbox[1], 3),
                "x_max_mm": round(bbox[2], 3),
                "y_max_mm": round(bbox[3], 3),
            }
            if bbox
            else None
        ),
        "usable_area": {
            "x_min_mm": round(usable["left"], 3),
            "y_min_mm": round(usable["bottom"], 3),
            "x_max_mm": round(usable["right"], 3),
            "y_max_mm": round(usable["top"], 3),
            "area_mm2": round(usable["area_mm2"], 3),
        },
        "espacios_muertos_aproximados": dead_spaces,
    }


def generar_repeat(layout: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    updated = deepcopy(layout)
    if isinstance(config, dict):
        for key, value in config.items():
            if value is not None:
                updated[key] = value
    updated["imposition_engine"] = "repeat"

    from routes import _build_step_repeat_slots

    updated["slots"] = _build_step_repeat_slots(updated)
    return updated


def centrar_layout(layout: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(layout)
    slots = _target_slots(updated, include_locked=False)
    bbox = _bbox(slots)
    usable = _sheet_bounds(updated)
    if not slots or not bbox or usable["width"] <= EPSILON or usable["height"] <= EPSILON:
        return updated

    min_x, min_y, max_x, max_y = bbox
    block_w = max_x - min_x
    block_h = max_y - min_y
    target_x = usable["left"] + max(0.0, usable["width"] - block_w) / 2.0
    target_y = usable["bottom"] + max(0.0, usable["height"] - block_h) / 2.0
    dx = target_x - min_x
    dy = target_y - min_y

    for slot in slots:
        slot["x_mm"] = _to_float(slot.get("x_mm")) + dx
        slot["y_mm"] = _to_float(slot.get("y_mm")) + dy
    return updated


def optimizar_repeat(layout: Dict[str, Any]) -> Dict[str, Any]:
    try:
        generated = generar_repeat(layout, {})
    except Exception:
        generated = deepcopy(layout)
    return centrar_layout(generated)


def aplicar_reglas_repeat(layout: Dict[str, Any], reglas: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    updated = deepcopy(layout)
    if not isinstance(reglas, dict):
        return updated

    priority = reglas.get("prioridad_por_diseno")
    designs = updated.get("designs")
    if isinstance(priority, dict) and isinstance(designs, list):
        designs.sort(key=lambda design: priority.get(design.get("ref"), priority.get(design.get("work_id"), 9999)))

    zona_sugerida = reglas.get("zona_sugerida")
    if zona_sugerida is not None:
        updated.setdefault("ai_agent", {})["zona_sugerida"] = zona_sugerida

    return updated
