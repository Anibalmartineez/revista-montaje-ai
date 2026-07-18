"""Canonical constants and type vocabulary for Layout V2.

Layout V2 is a clean contract.  It does not normalize or interpret fields from
the previous editor.  Persisted geometry always stores an unrotated trim size,
a separate uniform bleed and the trim centre on the sheet.
"""

from typing import Final


LAYOUT_SCHEMA_VERSION: Final = 2

VALID_FACES: Final = frozenset({"front", "back"})
VALID_DUPLEX_FLIPS: Final = frozenset({"none", "long_edge", "short_edge"})
VALID_PDF_BOXES: Final = frozenset({"media", "trim", "bleed", "crop"})
VALID_ASSET_STATUSES: Final = frozenset({"uploaded", "processing", "ready", "error"})
VALID_PREFLIGHT_STATUSES: Final = frozenset({"not_run", "pass", "warning", "error"})
VALID_ISSUE_LEVELS: Final = frozenset({"info", "warning", "error"})
VALID_FIT_MODES: Final = frozenset({"actual_size", "contain", "cover", "stretch"})
VALID_CLIP_TARGETS: Final = frozenset({"none", "trim_box", "bleed_box"})
VALID_LOCK_SOURCES: Final = frozenset({"user", "ctp", "engine", "system"})
VALID_GENERATOR_TYPES: Final = frozenset(
    {"manual", "engine", "duplicate", "duplex_copy", "ai"}
)
VALID_ENGINES: Final = frozenset({"manual", "repeat", "nesting", "hybrid"})
VALID_RENDER_MODES: Final = frozenset({"raster", "vector_hybrid"})
VALID_BLEED_POLICIES: Final = frozenset({"slot_geometry"})
VALID_IMPOSITION_STATUSES: Final = frozenset(
    {"complete", "incomplete", "failed"}
)

LEGACY_FIELD_NAMES: Final = frozenset(
    {
        "w_mm",
        "h_mm",
        "slot_box_final",
        "design_export",
        "designs",
        "bleed_default_mm",
        "gap_default_mm",
        "spacingSettings",
        "snapSettings",
        "active_face",
    }
)

EXPECTED_COORDINATE_SYSTEM: Final = {
    "unit": "mm",
    "origin": "bottom_left",
    "x_axis": "right",
    "y_axis": "up",
    "rotation_direction": "counter_clockwise",
    "rotation_origin": "trim_center",
}

CARDINAL_ROTATIONS_DEG: Final = frozenset({0.0, 90.0, 180.0, 270.0})


def is_layout_v2(value: object) -> bool:
    """Return whether *value* explicitly declares the Layout V2 contract."""

    return isinstance(value, dict) and value.get("layout_schema_version") == 2
