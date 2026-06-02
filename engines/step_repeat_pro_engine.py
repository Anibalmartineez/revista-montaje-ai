import math
from typing import Dict, List

from services.editor_offset_layout_defaults import (
    REPEAT_DESIGN_DEFAULT_PRIORITY,
    REPEAT_DESIGN_ZONES,
    first_numeric,
    layout_spacing_gaps,
    normalize_repeat_design_metadata,
)


class IncompleteImpositionError(ValueError):
    def __init__(self, message: str, details: List[Dict] | None = None):
        super().__init__(message)
        self.details = details or []


def sheet_area(layout: Dict) -> tuple[float, float, float, float, float, float]:
    sheet_w, sheet_h = layout.get("sheet_mm", [0, 0])
    margins = layout.get("margins_mm", [0, 0, 0, 0])
    left, right, top, bottom = (margins + [0, 0, 0, 0])[:4]
    usable_w = max(0.0, float(sheet_w) - float(left) - float(right))
    usable_h = max(0.0, float(sheet_h) - float(top) - float(bottom))
    return usable_w, usable_h, float(left), float(right), float(top), float(bottom)


def design_dimensions(design: Dict, layout: Dict) -> tuple[float, float, float]:
    bleed = first_numeric(design.get("bleed_mm"), layout.get("bleed_default_mm"), default=0.0)
    width = first_numeric(design.get("width_mm"), default=0.0)
    height = first_numeric(design.get("height_mm"), default=0.0)
    return width + 2 * bleed, height + 2 * bleed, bleed


def ordered_repeat_designs(layout: Dict) -> List[Dict]:
    designs = layout.get("designs") or []
    normalized: List[tuple[int, Dict]] = []
    for idx, design in enumerate(designs):
        if not isinstance(design, dict):
            continue
        item = dict(design)
        normalize_repeat_design_metadata(item)
        normalized.append((idx, item))

    if normalized:
        max_forms = max(max(1, int(pair[1].get("forms_per_plate") or 1)) for pair in normalized)
        max_area = max(
            max(0.0, first_numeric(pair[1].get("width_mm"), default=0.0))
            * max(0.0, first_numeric(pair[1].get("height_mm"), default=0.0))
            for pair in normalized
        )
        ranked = sorted(
            normalized,
            key=lambda pair: (
                -max(1, int(pair[1].get("forms_per_plate") or 1)),
                pair[0],
            ),
        )
        primary_idx = ranked[0][0]

        next_priority = 1
        for idx, design in ranked:
            overrides = design.get("repeat_manual_overrides") or {}
            forms = max(1, int(design.get("forms_per_plate") or 1))
            area = (
                max(0.0, first_numeric(design.get("width_mm"), default=0.0))
                * max(0.0, first_numeric(design.get("height_mm"), default=0.0))
            )
            zone = str(design.get("preferred_zone") or "auto").strip().lower()

            if not overrides.get("repeat_role"):
                auto_role = "secondary"
                if idx == primary_idx:
                    auto_role = "primary"
                elif zone == "fill":
                    auto_role = "fill"
                elif zone == "auto" and forms == 1 and max_forms >= 3 and area > 0 and max_area > 0 and area <= max_area * 0.5:
                    auto_role = "fill"
                design["repeat_role"] = auto_role

            if not overrides.get("priority"):
                design["priority"] = float(next_priority)
                next_priority += 1

    return [
        design
        for _, design in sorted(
            normalized,
            key=lambda pair: (
                1 if pair[1].get("repeat_role") == "fill" else 0,
                first_numeric(pair[1].get("priority"), default=REPEAT_DESIGN_DEFAULT_PRIORITY),
                pair[0],
            ),
        )
    ]


def design_repeat_zone(design: Dict) -> str:
    zone = str(design.get("preferred_zone") or "auto").strip().lower()
    if zone not in REPEAT_DESIGN_ZONES:
        zone = "auto"
    if zone not in {"auto", "fill"}:
        return zone
    if zone == "fill" or design.get("repeat_role") == "fill":
        return "fill"
    return zone


def group_designs_by_zone(designs: List[Dict]) -> Dict[str, List[Dict]]:
    groups = {zone: [] for zone in ["auto", "top", "bottom", "left", "right", "center", "fill"]}
    for design in designs:
        groups.setdefault(design_repeat_zone(design), []).append(design)
    return groups


def get_zone_bounds(layout: Dict, zone: str) -> tuple[float, float, float, float]:
    usable_w, usable_h, left, _, _, bottom = sheet_area(layout)
    top_band_h = usable_h * 0.25
    bottom_band_h = usable_h * 0.25
    middle_bottom = bottom + bottom_band_h
    middle_h = max(0.0, usable_h - top_band_h - bottom_band_h)
    side_w = usable_w * 0.25

    if zone == "top":
        return left, bottom + usable_h - top_band_h, usable_w, top_band_h
    if zone == "bottom":
        return left, bottom, usable_w, bottom_band_h
    if zone == "left":
        return left, middle_bottom, side_w, middle_h
    if zone == "right":
        return left + usable_w - side_w, middle_bottom, side_w, middle_h
    if zone == "center":
        return left + side_w, middle_bottom, max(0.0, usable_w - 2 * side_w), middle_h
    return left, bottom, usable_w, usable_h


def slot_overlaps_existing(candidate: Dict, existing_slots: List[Dict]) -> bool:
    x = first_numeric(candidate.get("x_mm"), default=0.0)
    y = first_numeric(candidate.get("y_mm"), default=0.0)
    w = first_numeric(candidate.get("w_mm"), default=0.0)
    h = first_numeric(candidate.get("h_mm"), default=0.0)
    right = x + w
    top = y + h
    for slot in existing_slots:
        sx = first_numeric(slot.get("x_mm"), default=0.0)
        sy = first_numeric(slot.get("y_mm"), default=0.0)
        sr = sx + first_numeric(slot.get("w_mm"), default=0.0)
        st = sy + first_numeric(slot.get("h_mm"), default=0.0)
        if x < sr and right > sx and y < st and top > sy:
            return True
    return False


def repeat_requested_vs_placed(
    designs: List[Dict],
    slots: List[Dict],
    placement_attempts: Dict[str, int] | None = None,
) -> List[Dict]:
    placed_by_ref: Dict[str, int] = {}
    for slot in slots:
        ref = slot.get("design_ref")
        if ref is None:
            continue
        ref_key = str(ref)
        placed_by_ref[ref_key] = placed_by_ref.get(ref_key, 0) + 1

    summary: List[Dict] = []
    for design in designs:
        if not isinstance(design, dict):
            continue
        ref = design.get("ref")
        if ref is None:
            continue
        ref_key = str(ref)
        requested = max(1, int(design.get("forms_per_plate") or 1))
        placed = int(placed_by_ref.get(ref_key, 0))
        if placement_attempts:
            placed = max(placed, int(placement_attempts.get(ref_key, 0)))
        missing = max(0, requested - placed)
        summary.append(
            {
                "design_ref": ref_key,
                "filename": design.get("filename"),
                "preferred_zone": design.get("preferred_zone") or "auto",
                "requested_forms": requested,
                "placed_forms": placed,
                "missing_forms": missing,
            }
        )
    return summary


def repeat_capacity(
    slot_w: float,
    slot_h: float,
    usable_w: float,
    usable_h: float,
    gap_x: float,
    gap_y: float,
) -> tuple[int, int, int]:
    if slot_w <= 0 or slot_h <= 0 or usable_w <= 0 or usable_h <= 0:
        return 0, 0, 0
    cols = int((usable_w + gap_x) // (slot_w + gap_x)) if slot_w + gap_x > 0 else 0
    rows = int((usable_h + gap_y) // (slot_h + gap_y)) if slot_h + gap_y > 0 else 0
    cols = max(0, cols)
    rows = max(0, rows)
    return cols, rows, cols * rows


def choose_repeat_orientation(
    piece_w: float,
    piece_h: float,
    forms: int,
    allow_rotation: bool,
    usable_w: float,
    remaining_h: float,
    gap_x: float,
    gap_y: float,
) -> tuple[float, float, int, int]:
    cols_0, _, capacity_0 = repeat_capacity(piece_w, piece_h, usable_w, remaining_h, gap_x, gap_y)
    if not allow_rotation or capacity_0 >= forms:
        return piece_w, piece_h, 0, cols_0

    cols_90, _, capacity_90 = repeat_capacity(piece_h, piece_w, usable_w, remaining_h, gap_x, gap_y)
    if capacity_90 > capacity_0:
        return piece_h, piece_w, 90, cols_90

    return piece_w, piece_h, 0, cols_0


def append_step_repeat_slots_in_bounds(
    slots: List[Dict],
    designs: List[Dict],
    layout: Dict,
    bounds: tuple[float, float, float, float],
    gap_x: float,
    gap_y: float,
    active_face: str,
    avoid_existing: bool = False,
    placement_attempts: Dict[str, int] | None = None,
) -> Dict | None:
    left, bottom, usable_w, usable_h = bounds
    if usable_w <= 0 or usable_h <= 0:
        return None

    group_start = len(slots)
    cursor_y = bottom
    sheet_top = bottom + usable_h

    for design in designs:
        design_ref = str(design.get("ref") or "")
        piece_w, piece_h, bleed = design_dimensions(design, layout)
        allow_rotation = bool(design.get("allow_rotation", True))
        forms = max(1, int(design.get("forms_per_plate") or 1))
        remaining_h = sheet_top - cursor_y
        slot_w, slot_h, rot, cols = choose_repeat_orientation(
            piece_w,
            piece_h,
            forms,
            allow_rotation,
            usable_w,
            remaining_h,
            gap_x,
            gap_y,
        )
        if cols <= 0:
            if placement_attempts is not None and design_ref:
                placement_attempts[design_ref] = max(placement_attempts.get(design_ref, 0), 0)
            return None

        rows_used = 0
        placed = 0
        idx = 0
        design_slots: List[Dict] = []
        while placed < forms:
            col = idx % cols
            row = idx // cols
            x_mm = left + col * (slot_w + gap_x)
            y_mm = cursor_y + row * (slot_h + gap_y)

            if x_mm + slot_w > left + usable_w + 1e-6 or y_mm + slot_h > sheet_top + 1e-6:
                if placement_attempts is not None and design_ref:
                    placement_attempts[design_ref] = max(placement_attempts.get(design_ref, 0), placed)
                return None
            rows_used = max(rows_used, row + 1)

            candidate = {
                "id": f"sr_{len(slots) + len(design_slots)}",
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": slot_w,
                "h_mm": slot_h,
                "rotation_deg": rot,
                "logical_work_id": design.get("work_id"),
                "bleed_mm": bleed,
                "crop_marks": True,
                "locked": False,
                "design_ref": design.get("ref"),
                "face": active_face,
            }

            target_slots = slots + design_slots if avoid_existing else design_slots
            if not avoid_existing or not slot_overlaps_existing(candidate, target_slots):
                design_slots.append(candidate)
                placed += 1
            idx += 1

        if placement_attempts is not None and design_ref:
            placement_attempts[design_ref] = max(placement_attempts.get(design_ref, 0), placed)
        slots.extend(design_slots)

        if rows_used:
            cursor_y += rows_used * slot_h + max(0, rows_used - 1) * gap_y + gap_y

    group_end = len(slots)
    if group_end <= group_start:
        return None
    return {
        "start": group_start,
        "end": group_end,
        "bounds": bounds,
    }


def candidate_positions_for_fill(
    bounds: tuple[float, float, float, float],
    slot_w: float,
    slot_h: float,
    gap_x: float,
    gap_y: float,
) -> List[tuple[float, float]]:
    left, bottom, usable_w, usable_h = bounds
    if slot_w <= 0 or slot_h <= 0 or usable_w <= 0 or usable_h <= 0:
        return []
    max_x = left + usable_w - slot_w
    max_y = bottom + usable_h - slot_h
    if max_x < left - 1e-6 or max_y < bottom - 1e-6:
        return []

    step_x = max(slot_w + gap_x, slot_w, 1.0)
    step_y = max(slot_h + gap_y, slot_h, 1.0)

    xs: List[float] = []
    x = left
    while x <= max_x + 1e-6:
        xs.append(x)
        x += step_x
    if not xs or abs(xs[-1] - max_x) > 1e-6:
        xs.append(max_x)

    ys: List[float] = []
    y = bottom
    while y <= max_y + 1e-6:
        ys.append(y)
        y += step_y
    if not ys or abs(ys[-1] - max_y) > 1e-6:
        ys.append(max_y)

    candidates: List[tuple[float, float]] = []
    seen: set[tuple[int, int]] = set()

    def add_candidate(x_pos: float, y_pos: float) -> None:
        key = (round(x_pos * 1000), round(y_pos * 1000))
        if key in seen:
            return
        seen.add(key)
        candidates.append((x_pos, y_pos))

    for y_pos in ys:
        for x_pos in xs:
            add_candidate(x_pos, y_pos)
    for y_pos in reversed(ys):
        for x_pos in xs:
            add_candidate(x_pos, y_pos)
    for x_pos in xs:
        for y_pos in ys:
            add_candidate(x_pos, y_pos)

    center_x = left + max(0.0, usable_w - slot_w) / 2.0
    center_y = bottom + max(0.0, usable_h - slot_h) / 2.0
    grid_points = [(x_pos, y_pos) for y_pos in ys for x_pos in xs]
    for x_pos, y_pos in sorted(
        grid_points,
        key=lambda point: (abs(point[0] - center_x) + abs(point[1] - center_y), point[1], point[0]),
    ):
        add_candidate(x_pos, y_pos)

    return candidates


def estimate_repeat_group_height(
    designs: List[Dict],
    layout: Dict,
    usable_w: float,
    usable_h: float,
    gap_x: float,
    gap_y: float,
) -> float | None:
    if usable_w <= 0 or usable_h <= 0:
        return None

    total_h = 0.0
    remaining_h = usable_h
    for design in designs:
        piece_w, piece_h, _ = design_dimensions(design, layout)
        allow_rotation = bool(design.get("allow_rotation", True))
        forms = max(1, int(design.get("forms_per_plate") or 1))
        slot_w, slot_h, _, cols = choose_repeat_orientation(
            piece_w,
            piece_h,
            forms,
            allow_rotation,
            usable_w,
            remaining_h,
            gap_x,
            gap_y,
        )
        if cols <= 0:
            return None
        rows = int(math.ceil(forms / cols))
        block_h = rows * slot_h + max(0, rows - 1) * gap_y + gap_y
        if block_h > remaining_h + 1e-6:
            return None
        total_h += block_h
        remaining_h = max(0.0, usable_h - total_h)
    return total_h


def expanded_vertical_zone_bounds(
    layout: Dict,
    zone_groups: Dict[str, List[Dict]],
    gap_x: float,
    gap_y: float,
) -> Dict[str, tuple[float, float, float, float]] | None:
    usable_w, usable_h, left, _, _, bottom = sheet_area(layout)
    if usable_w <= 0 or usable_h <= 0:
        return None

    vertical_order = ["bottom", "center", "top"]
    heights: Dict[str, float] = {}
    present = [zone for zone in vertical_order if zone_groups.get(zone)]
    if not present:
        return None

    for zone in present:
        height = estimate_repeat_group_height(zone_groups.get(zone, []), layout, usable_w, usable_h, gap_x, gap_y)
        if height is None:
            return None
        heights[zone] = height

    packed_height = sum(heights[zone] for zone in present)
    if packed_height > usable_h + 1e-6:
        return None

    if len(present) == 1:
        zone = present[0]
        height = heights[zone]
        if zone == "top":
            start_y = bottom + max(0.0, usable_h - height)
        elif zone == "bottom":
            start_y = bottom
        else:
            start_y = bottom + max(0.0, usable_h - height) / 2.0
        return {zone: (left, start_y, usable_w, height)}

    start_y = bottom + max(0.0, usable_h - packed_height) / 2.0
    bounds: Dict[str, tuple[float, float, float, float]] = {}
    current_y = start_y
    for zone in vertical_order:
        if zone not in heights:
            continue
        bounds[zone] = (left, current_y, usable_w, heights[zone])
        current_y += heights[zone]
    return bounds


def append_fill_slots_smart(
    slots: List[Dict],
    designs: List[Dict],
    layout: Dict,
    bounds: tuple[float, float, float, float],
    gap_x: float,
    gap_y: float,
    active_face: str,
    placement_attempts: Dict[str, int] | None = None,
) -> None:
    left, bottom, usable_w, usable_h = bounds
    if usable_w <= 0 or usable_h <= 0:
        return

    for design in designs:
        design_ref = str(design.get("ref") or "")
        piece_w, piece_h, bleed = design_dimensions(design, layout)
        allow_rotation = bool(design.get("allow_rotation", True))
        forms = max(1, int(design.get("forms_per_plate") or 1))
        slot_w, slot_h, rot, _ = choose_repeat_orientation(
            piece_w,
            piece_h,
            forms,
            allow_rotation,
            usable_w,
            usable_h,
            gap_x,
            gap_y,
        )
        candidates = candidate_positions_for_fill((left, bottom, usable_w, usable_h), slot_w, slot_h, gap_x, gap_y)
        placed = 0
        design_slots: List[Dict] = []
        for x_mm, y_mm in candidates:
            if placed >= forms:
                break
            candidate = {
                "id": f"sr_{len(slots) + len(design_slots)}",
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": slot_w,
                "h_mm": slot_h,
                "rotation_deg": rot,
                "logical_work_id": design.get("work_id"),
                "bleed_mm": bleed,
                "crop_marks": True,
                "locked": False,
                "design_ref": design.get("ref"),
                "face": active_face,
            }
            if slot_overlaps_existing(candidate, slots + design_slots):
                continue
            design_slots.append(candidate)
            placed += 1
        if placement_attempts is not None and design_ref:
            placement_attempts[design_ref] = max(placement_attempts.get(design_ref, 0), placed)
        if placed == forms:
            slots.extend(design_slots)


def slot_group_bbox(slots: List[Dict], start: int, end: int) -> tuple[float, float, float, float] | None:
    group = slots[start:end]
    if not group:
        return None
    min_x = min(first_numeric(slot.get("x_mm"), default=0.0) for slot in group)
    min_y = min(first_numeric(slot.get("y_mm"), default=0.0) for slot in group)
    max_x = max(first_numeric(slot.get("x_mm"), default=0.0) + first_numeric(slot.get("w_mm"), default=0.0) for slot in group)
    max_y = max(first_numeric(slot.get("y_mm"), default=0.0) + first_numeric(slot.get("h_mm"), default=0.0) for slot in group)
    return min_x, min_y, max_x, max_y


def translated_group_slots(slots: List[Dict], start: int, end: int, dx: float, dy: float) -> List[Dict]:
    translated: List[Dict] = []
    for slot in slots[start:end]:
        translated.append(
            {
                **slot,
                "x_mm": first_numeric(slot.get("x_mm"), default=0.0) + dx,
                "y_mm": first_numeric(slot.get("y_mm"), default=0.0) + dy,
            }
        )
    return translated


def can_place_translated_group(
    slots: List[Dict],
    start: int,
    end: int,
    translated_slots: List[Dict],
    usable_bounds: tuple[float, float, float, float],
) -> bool:
    left, bottom, usable_w, usable_h = usable_bounds
    right = left + usable_w
    top = bottom + usable_h
    others = slots[:start] + slots[end:]

    for slot in translated_slots:
        x = first_numeric(slot.get("x_mm"), default=0.0)
        y = first_numeric(slot.get("y_mm"), default=0.0)
        w = first_numeric(slot.get("w_mm"), default=0.0)
        h = first_numeric(slot.get("h_mm"), default=0.0)
        if x < left - 1e-6 or y < bottom - 1e-6 or x + w > right + 1e-6 or y + h > top + 1e-6:
            return False
        if slot_overlaps_existing(slot, others):
            return False
    return True


def compact_vertical_zone_groups(
    slots: List[Dict],
    group_ranges: Dict[str, Dict],
    usable_bounds: tuple[float, float, float, float],
    min_gap_y: float,
) -> None:
    present = []
    for zone in ["bottom", "center", "top"]:
        info = group_ranges.get(zone)
        if not info:
            continue
        bbox = slot_group_bbox(slots, info["start"], info["end"])
        if not bbox:
            continue
        present.append({"zone": zone, "start": info["start"], "end": info["end"], "bbox": bbox})

    if len(present) < 2:
        return

    total_height = sum(group["bbox"][3] - group["bbox"][1] for group in present)
    packed_height = total_height + max(0, len(present) - 1) * max(0.0, min_gap_y)
    left, bottom, usable_w, usable_h = usable_bounds
    if packed_height > usable_h + 1e-6:
        return

    target_y = bottom + max(0.0, usable_h - packed_height) / 2.0
    moved_groups = []
    for group in present:
        min_x, min_y, max_x, max_y = group["bbox"]
        height = max_y - min_y
        dy = target_y - min_y
        translated = translated_group_slots(slots, group["start"], group["end"], 0.0, dy)
        if not can_place_translated_group(slots, group["start"], group["end"], translated, usable_bounds):
            return
        moved_groups.append((group, translated))
        target_y += height + max(0.0, min_gap_y)

    for group, translated in moved_groups:
        slots[group["start"]:group["end"]] = translated


def translated_groups_are_safe(
    slots: List[Dict],
    translated_groups: List[tuple[Dict, List[Dict]]],
    usable_bounds: tuple[float, float, float, float],
) -> bool:
    left, bottom, usable_w, usable_h = usable_bounds
    right = left + usable_w
    top = bottom + usable_h
    moving_indices: set[int] = set()
    for group, _ in translated_groups:
        moving_indices.update(range(group["start"], group["end"]))
    outside_slots = [slot for idx, slot in enumerate(slots) if idx not in moving_indices]

    translated_slots: List[Dict] = []
    for _, group_slots in translated_groups:
        translated_slots.extend(group_slots)

    checked: List[Dict] = []
    for slot in translated_slots:
        x = first_numeric(slot.get("x_mm"), default=0.0)
        y = first_numeric(slot.get("y_mm"), default=0.0)
        w = first_numeric(slot.get("w_mm"), default=0.0)
        h = first_numeric(slot.get("h_mm"), default=0.0)
        if x < left - 1e-6 or y < bottom - 1e-6 or x + w > right + 1e-6 or y + h > top + 1e-6:
            return False
        if slot_overlaps_existing(slot, outside_slots) or slot_overlaps_existing(slot, checked):
            return False
        checked.append(slot)
    return True


def compact_vertical_zonal_and_auto_groups(
    slots: List[Dict],
    group_ranges: Dict[str, Dict],
    usable_bounds: tuple[float, float, float, float],
    min_gap_y: float,
) -> None:
    if not group_ranges.get("auto") or not any(group_ranges.get(zone) for zone in ["bottom", "center", "top"]):
        return

    present = []
    for zone in ["bottom", "center", "top", "auto"]:
        info = group_ranges.get(zone)
        if not info:
            continue
        bbox = slot_group_bbox(slots, info["start"], info["end"])
        if not bbox:
            continue
        present.append({"zone": zone, "start": info["start"], "end": info["end"], "bbox": bbox})

    if len(present) < 2:
        return

    present.sort(key=lambda group: (group["bbox"][1], group["bbox"][0]))
    total_height = sum(group["bbox"][3] - group["bbox"][1] for group in present)
    packed_height = total_height + max(0, len(present) - 1) * max(0.0, min_gap_y)
    left, bottom, usable_w, usable_h = usable_bounds
    if packed_height > usable_h + 1e-6:
        return

    target_y = bottom + max(0.0, usable_h - packed_height) / 2.0
    translated_groups: List[tuple[Dict, List[Dict]]] = []
    for group in present:
        min_x, min_y, max_x, max_y = group["bbox"]
        height = max_y - min_y
        dy = target_y - min_y
        translated = translated_group_slots(slots, group["start"], group["end"], 0.0, dy)
        translated_groups.append((group, translated))
        target_y += height + max(0.0, min_gap_y)

    if not translated_groups_are_safe(slots, translated_groups, usable_bounds):
        return

    for group, translated in translated_groups:
        slots[group["start"]:group["end"]] = translated


def build_step_repeat_slots(layout: Dict) -> List[Dict]:
    designs = ordered_repeat_designs(layout)
    if not designs:
        raise ValueError("No hay diseños configurados para aplicar Step & Repeat.")
    usable_w, usable_h, left, _, _, bottom = sheet_area(layout)
    if usable_w <= 0 or usable_h <= 0:
        return []

    gap_x, gap_y = layout_spacing_gaps(layout)
    slots: List[Dict] = []
    active_face = layout.get("active_face") or "front"
    group_ranges: Dict[str, Dict] = {}
    placement_attempts: Dict[str, int] = {}

    zone_groups = group_designs_by_zone(designs)
    zonal_order = ["top", "left", "center", "right", "bottom"]
    has_zonal_designs = any(zone_groups.get(zone) for zone in zonal_order)
    has_fill_designs = bool(zone_groups.get("fill"))

    if not has_zonal_designs and not has_fill_designs:
        append_step_repeat_slots_in_bounds(
            slots,
            designs,
            layout,
            (left, bottom, usable_w, usable_h),
            gap_x,
            gap_y,
            active_face,
            placement_attempts=placement_attempts,
        )
        placement_summary = repeat_requested_vs_placed(designs, slots, placement_attempts)
        incomplete = [item for item in placement_summary if item["missing_forms"] > 0]
        if incomplete:
            messages = []
            for item in incomplete:
                design_name = item.get("filename") or item.get("design_ref")
                messages.append(
                    f"Diseño {design_name}: solicitadas {item['requested_forms']}, "
                    f"colocadas {item['placed_forms']}, faltan {item['missing_forms']}."
                )
            raise IncompleteImpositionError(
                "No entran todas las formas solicitadas en el pliego. " + " ".join(messages),
                details=incomplete,
            )
        return slots

    if has_zonal_designs:
        for zone in zonal_order:
            group_info = append_step_repeat_slots_in_bounds(
                slots,
                zone_groups.get(zone, []),
                layout,
                get_zone_bounds(layout, zone),
                gap_x,
                gap_y,
                active_face,
                placement_attempts=placement_attempts,
            )
            if group_info:
                group_ranges[zone] = group_info

        compact_vertical_zone_groups(
            slots,
            group_ranges,
            (left, bottom, usable_w, usable_h),
            max(0.0, first_numeric(gap_y, layout.get("gap_default_mm"), default=5.0)),
        )

        vertical_retry_allowed = (
            not zone_groups.get("left")
            and not zone_groups.get("right")
            and any(zone_groups.get(zone) for zone in ["top", "center", "bottom"])
        )
        zonal_summary = repeat_requested_vs_placed(designs, slots, placement_attempts)
        zonal_incomplete = [
            item
            for item in zonal_summary
            if item["missing_forms"] > 0 and str(item.get("preferred_zone") or "auto") in {"top", "center", "bottom"}
        ]

        if vertical_retry_allowed and zonal_incomplete:
            expanded_bounds = expanded_vertical_zone_bounds(layout, zone_groups, gap_x, gap_y)
            if expanded_bounds:
                retry_slots: List[Dict] = []
                retry_group_ranges: Dict[str, Dict] = {}
                retry_attempts: Dict[str, int] = {}
                retry_failed = False

                for zone in ["bottom", "center", "top"]:
                    if not zone_groups.get(zone):
                        continue
                    group_info = append_step_repeat_slots_in_bounds(
                        retry_slots,
                        zone_groups.get(zone, []),
                        layout,
                        expanded_bounds[zone],
                        gap_x,
                        gap_y,
                        active_face,
                        placement_attempts=retry_attempts,
                    )
                    if group_info:
                        retry_group_ranges[zone] = group_info
                    else:
                        retry_failed = True
                        break

                if not retry_failed:
                    compact_vertical_zone_groups(
                        retry_slots,
                        retry_group_ranges,
                        (left, bottom, usable_w, usable_h),
                        max(0.0, first_numeric(gap_y, layout.get("gap_default_mm"), default=5.0)),
                    )
                    retry_summary = repeat_requested_vs_placed(designs, retry_slots, retry_attempts)
                    retry_incomplete = [
                        item
                        for item in retry_summary
                        if item["missing_forms"] > 0 and str(item.get("preferred_zone") or "auto") in {"top", "center", "bottom"}
                    ]
                    if not retry_incomplete:
                        slots = retry_slots
                        group_ranges = retry_group_ranges
                        placement_attempts = retry_attempts

    auto_group_info = append_step_repeat_slots_in_bounds(
        slots,
        zone_groups.get("auto", []),
        layout,
        (left, bottom, usable_w, usable_h),
        gap_x,
        gap_y,
        active_face,
        avoid_existing=True,
        placement_attempts=placement_attempts,
    )
    if auto_group_info:
        group_ranges["auto"] = auto_group_info

    if (
        any(zone_groups.get(zone) for zone in ["top", "center", "bottom"])
        and zone_groups.get("auto")
        and not zone_groups.get("left")
        and not zone_groups.get("right")
    ):
        compact_vertical_zonal_and_auto_groups(
            slots,
            group_ranges,
            (left, bottom, usable_w, usable_h),
            max(0.0, first_numeric(gap_y, layout.get("gap_default_mm"), default=5.0)),
        )

    append_fill_slots_smart(
        slots,
        zone_groups.get("fill", []),
        layout,
        (left, bottom, usable_w, usable_h),
        gap_x,
        gap_y,
        active_face,
        placement_attempts=placement_attempts,
    )

    placement_summary = repeat_requested_vs_placed(designs, slots, placement_attempts)
    incomplete = [item for item in placement_summary if item["missing_forms"] > 0]
    if incomplete:
        messages = []
        for item in incomplete:
            design_name = item.get("filename") or item.get("design_ref")
            messages.append(
                f"Diseño {design_name}: solicitadas {item['requested_forms']}, "
                f"colocadas {item['placed_forms']}, faltan {item['missing_forms']}."
            )
        raise IncompleteImpositionError(
            "No entran todas las formas solicitadas en el pliego. " + " ".join(messages),
            details=incomplete,
        )

    return slots
