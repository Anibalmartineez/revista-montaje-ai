import math
from typing import Dict


REPEAT_DESIGN_DEFAULT_PRIORITY = 100
REPEAT_DESIGN_ZONES = {"auto", "top", "bottom", "left", "right", "center", "fill"}
REPEAT_DESIGN_FLOWS = {"auto", "horizontal", "vertical"}
REPEAT_DESIGN_ROLES = {"primary", "secondary", "fill"}


def default_constructor_layout() -> Dict:
    return {
        "sheet_mm": [640, 880],
        "margins_mm": [10, 10, 10, 10],
        "bleed_default_mm": 3,
        "gap_default_mm": 5,
        "works": [],
        "slots": [],
        "designs": [],
        "export_settings": {"bleed_mm": 3, "crop_marks": True, "output_mode": "raster"},
        "design_export": {},
        "faces": ["front"],
        "active_face": "front",
        "imposition_engine": "repeat",
        "allowed_engines": ["repeat", "nesting", "hybrid"],
    }


def ensure_faces_fields(layout: Dict) -> tuple[Dict, bool]:
    changed = False
    if not isinstance(layout, dict):
        return layout, changed

    faces = layout.get("faces")
    if not isinstance(faces, list) or len(faces) == 0:
        layout["faces"] = ["front"]
        changed = True

    active_face = layout.get("active_face")
    if not active_face or active_face not in layout["faces"]:
        layout["active_face"] = layout["faces"][0]
        changed = True

    slots = layout.get("slots")
    if isinstance(slots, list):
        for slot in slots:
            if isinstance(slot, dict) and not slot.get("face"):
                slot["face"] = "front"
                changed = True

    return layout, changed


def normalize_repeat_manual_overrides(design: Dict) -> bool:
    changed = False
    overrides = design.get("repeat_manual_overrides")
    if not isinstance(overrides, dict):
        overrides = {}
        changed = True

    default_markers = {
        "priority": REPEAT_DESIGN_DEFAULT_PRIORITY,
        "preferred_flow": "auto",
        "repeat_role": "secondary",
    }
    normalized: Dict[str, bool] = {}
    for field, default_value in default_markers.items():
        raw = overrides.get(field)
        if isinstance(raw, bool):
            normalized[field] = raw
            continue
        current = design.get(field)
        if field == "priority":
            try:
                current = float(current)
            except (TypeError, ValueError):
                current = float(REPEAT_DESIGN_DEFAULT_PRIORITY)
            normalized[field] = bool(current != float(default_value))
        else:
            normalized[field] = str(current or default_value).strip().lower() != str(default_value)
        changed = True

    if design.get("repeat_manual_overrides") != normalized:
        design["repeat_manual_overrides"] = normalized
        changed = True
    return changed


def normalize_repeat_design_metadata(design: Dict) -> bool:
    changed = False
    if normalize_repeat_manual_overrides(design):
        changed = True

    raw_priority = design.get("priority")
    try:
        priority = float(raw_priority)
        if not math.isfinite(priority):
            raise ValueError
    except (TypeError, ValueError):
        priority = float(REPEAT_DESIGN_DEFAULT_PRIORITY)
    if raw_priority != priority:
        design["priority"] = priority
        changed = True

    def _normalize_choice(field: str, allowed: set[str], default: str) -> None:
        nonlocal changed
        value = str(design.get(field) or default).strip().lower()
        if value not in allowed:
            value = default
        if design.get(field) != value:
            design[field] = value
            changed = True

    _normalize_choice("preferred_zone", REPEAT_DESIGN_ZONES, "auto")
    _normalize_choice("preferred_flow", REPEAT_DESIGN_FLOWS, "auto")
    _normalize_choice("repeat_role", REPEAT_DESIGN_ROLES, "secondary")
    return changed


def ensure_imposition_fields(layout: Dict) -> tuple[Dict, bool]:
    changed = False
    if not isinstance(layout, dict):
        return layout, changed

    allowed = layout.get("allowed_engines")
    if not isinstance(allowed, list) or not allowed:
        layout["allowed_engines"] = ["repeat", "nesting", "hybrid"]
        allowed = layout["allowed_engines"]
        changed = True

    engine = layout.get("imposition_engine")
    if engine not in allowed:
        layout["imposition_engine"] = allowed[0]
        changed = True

    designs = layout.get("designs", [])
    for design in designs:
        if not isinstance(design, dict):
            continue
        if "forms_per_plate" not in design:
            design["forms_per_plate"] = 1
            changed = True
        if "allow_rotation" not in design:
            design["allow_rotation"] = True
            changed = True
        if "bleed_mm" not in design:
            design["bleed_mm"] = layout.get("bleed_default_mm", 0)
            changed = True
        if normalize_repeat_design_metadata(design):
            changed = True

    return layout, changed


def first_numeric(*values, default: float = 0.0) -> float:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return float(default)


def layout_spacing_gaps(layout: Dict) -> tuple[float, float]:
    spacing = layout.get("spacingSettings") or layout.get("spacing_settings") or {}
    spacing_x = spacing.get("spacingX_mm") if isinstance(spacing, dict) else None
    spacing_y = spacing.get("spacingY_mm") if isinstance(spacing, dict) else None
    fallback_gap = layout.get("gap_default_mm")
    return (
        first_numeric(spacing_x, fallback_gap, default=0.0),
        first_numeric(spacing_y, fallback_gap, default=0.0),
    )


def ensure_export_fields(layout: Dict) -> tuple[Dict, bool]:
    changed = False
    if not isinstance(layout, dict):
        return layout, changed

    export_settings = layout.get("export_settings")
    if not isinstance(export_settings, dict):
        layout["export_settings"] = {
            "bleed_mm": 3,
            "crop_marks": True,
            "output_mode": "raster",
        }
        changed = True
    else:
        if export_settings.get("bleed_mm") is None:
            export_settings["bleed_mm"] = 3
            changed = True
        if export_settings.get("crop_marks") is None:
            export_settings["crop_marks"] = True
            changed = True
        if export_settings.get("output_mode") is None:
            export_settings["output_mode"] = "raster"
            changed = True

    if not isinstance(layout.get("design_export"), dict):
        layout["design_export"] = {}
        changed = True

    return layout, changed


def ensure_constructor_layout_defaults(layout: Dict) -> tuple[Dict, bool]:
    layout, changed_faces = ensure_faces_fields(layout)
    layout, changed_imposition = ensure_imposition_fields(layout)
    layout, changed_export = ensure_export_fields(layout)
    return layout, changed_faces or changed_imposition or changed_export
