from typing import Dict, List

from engines.nesting_pro_engine import NestingResult, compute_nesting
from engines import step_repeat_pro_engine
from services.editor_offset_layout_defaults import first_numeric, layout_spacing_gaps


IncompleteImpositionError = step_repeat_pro_engine.IncompleteImpositionError


def select_imposition_engine(
    layout: Dict,
    payload_layout: Dict | None = None,
    selected_engine: str | None = None,
) -> str:
    allowed = layout.get("allowed_engines") or ["repeat", "nesting", "hybrid"]
    engine = (
        selected_engine
        or (payload_layout or {}).get("imposition_engine")
        or layout.get("imposition_engine")
        or allowed[0]
    )
    if engine not in allowed:
        engine = allowed[0]
    return engine


def slots_from_nesting_result(result: NestingResult, layout: Dict) -> List[Dict]:
    active_face = layout.get("active_face") or "front"
    slots: List[Dict] = []
    for idx, slot in enumerate(result.slots):
        slots.append(
            {
                "id": f"nest_{idx}",
                "x_mm": float(slot.get("x_mm", 0)),
                "y_mm": float(slot.get("y_mm", 0)),
                "w_mm": float(slot.get("w_mm", 0)),
                "h_mm": float(slot.get("h_mm", 0)),
                "rotation_deg": int(slot.get("rotation_deg", 0)) % 360,
                "logical_work_id": None,
                "bleed_mm": first_numeric(slot.get("bleed_mm"), layout.get("bleed_default_mm"), default=0.0),
                "crop_marks": True,
                "locked": False,
                "design_ref": slot.get("design_ref") or slot.get("file"),
                "face": active_face,
            }
        )
    return slots


def repeat_pattern_over_sheet(
    base_slots: List[Dict],
    bbox: tuple[float, float, float, float],
    layout: Dict,
) -> List[Dict]:
    if not base_slots:
        return []
    usable_w, usable_h, left, _, _, bottom = step_repeat_pro_engine.sheet_area(layout)
    if usable_w <= 0 or usable_h <= 0:
        return []
    min_x, min_y, max_x, max_y = bbox
    block_w = max(0.0, max_x - min_x)
    block_h = max(0.0, max_y - min_y)
    if block_w <= 0 or block_h <= 0:
        return base_slots

    gap_x, gap_y = layout_spacing_gaps(layout)
    slots: List[Dict] = []
    y_offset = bottom
    while y_offset + block_h <= bottom + usable_h + 1e-6:
        x_offset = left
        while x_offset + block_w <= left + usable_w + 1e-6:
            for slot in base_slots:
                slots.append(
                    {
                        **slot,
                        "id": f"hyb_{len(slots)}",
                        "x_mm": x_offset + (slot["x_mm"] - min_x),
                        "y_mm": y_offset + (slot["y_mm"] - min_y),
                    }
                )
            x_offset += block_w + gap_x
        y_offset += block_h + gap_y
    return slots


def apply_imposition_engine(layout: Dict, engine: str) -> List[Dict]:
    if engine == "nesting":
        nesting = compute_nesting(layout)
        return slots_from_nesting_result(nesting, layout)
    if engine == "hybrid":
        nesting = compute_nesting(layout)
        base_slots = slots_from_nesting_result(nesting, layout)
        return repeat_pattern_over_sheet(base_slots, nesting.bbox, layout)
    return step_repeat_pro_engine.build_step_repeat_slots(layout)
